import streamlit as st
import hashlib
import secrets

# Set page config must be the first Streamlit command
st.set_page_config(
    page_title="Todo List App",
    page_icon="🎯",
    initial_sidebar_state="collapsed",
)

from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, Optional
import sqlalchemy as sa
from sqlalchemy import Boolean, Column, Date, Integer, MetaData, String, Table
from streamlit.connections import SQLConnection
import pandas as pd
import uuid
import streamlit_cookies_manager as cookies

# --- Authentication Functions ---
def hash_password(password, salt=None):
    """Hash a password with salt using SHA-256"""
    if salt is None:
        salt = secrets.token_hex(16)
    
    # Combine password and salt, then hash
    pw_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return pw_hash, salt

def verify_password(password, stored_hash, salt):
    """Verify a password against a stored hash"""
    pw_hash, _ = hash_password(password, salt)
    return pw_hash == stored_hash

def create_user(conn, username, email, password, full_name=None):
    """Create a new user in the database"""
    # Check if user already exists
    with conn.session as session:
        # Check if username is already taken
        stmt = sa.select(sa.text("id")).select_from(sa.table("users")).where(sa.text("username = :username"))
        result = session.execute(stmt, {"username": username})
        if result.first():
            return False, "Username already exists"
        
        # Check if email is already taken  
        stmt = sa.select(sa.text("id")).select_from(sa.table("users")).where(sa.text("email = :email"))
        result = session.execute(stmt, {"email": email})
        if result.first():
            return False, "Email already exists"
        
        # Hash the password
        pw_hash, salt = hash_password(password)
        
        # Create the user
        stmt = sa.text("""
            INSERT INTO users (username, email, full_name, password_hash, salt, created_at) 
            VALUES (:username, :email, :full_name, :pw_hash, :salt, :created_at)
            RETURNING id
        """)
        result = session.execute(
            stmt, 
            {
                "username": username, 
                "email": email, 
                "full_name": full_name, 
                "pw_hash": pw_hash, 
                "salt": salt,
                "created_at": datetime.now()
            }
        )
        user_id = result.scalar()
        session.commit()
        
        return True, user_id

def authenticate_user(conn, username, password):
    """Authenticate a user by username and password"""
    with conn.session as session:
        # Get user by username
        stmt = sa.text("""
            SELECT id, username, email, full_name, password_hash, salt 
            FROM users 
            WHERE username = :username
        """)
        result = session.execute(stmt, {"username": username})
        user = result.first()
        
        if user and verify_password(password, user.password_hash, user.salt):
            return True, {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name
            }
        
        return False, "Invalid username or password"

# --- MongoDB setup ---
from pymongo.mongo_client import MongoClient
import certifi

uri = "mongodb+srv://kochyanlv:qwerty12345@cluster71234.ifyaey3.mongodb.net/?retryWrites=true&w=majority&appName=Cluster71234"
mongo_client = MongoClient(uri, tlsCAFile=certifi.where())
mongo_db = mongo_client["todo_db"]
documents_collection = mongo_db["documents"]

# --- App Title ---
col1, col2 = st.columns([2, 1])
with col1:
    st.write("<h2><b>📝 <u>Database Todo List App</b></h2>", unsafe_allow_html=True)
    st.write(
        "<i>A multi-user todo dashboard built with :red[🚀 Streamlit] and:blue[🧙‍♂️SQLAlchemy] that stores and retrieves task data from a SQL database. A Table view is available for tracking all todos in one place. </i>",
        unsafe_allow_html=True)
    st.write(
        "<b><b>Note: :violet[🛠️ Database] access typically requires login, so this app uses a global database for demo purposes.</b></b>",
        unsafe_allow_html=True)
with col2:
    st.image("todo dog.gif")
# --- Connect to DB and Table ---
TABLE_NAME = "dashboard"
conn = st.connection("tasks_db", ttl=5 * 60)

from models import dashboard as dashboard_table
from models import metadata_obj as dashboard_metadata

# --- Authentication System ---
def login_page():
    """Display the login page with options to login or register"""
    st.subheader("Login to Your Account")
    
    # Login form
    with st.form("login_form"):
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        
        col1, col2 = st.columns(2)
        login_submitted = col1.form_submit_button("Login")
        show_register = col2.form_submit_button("Register Instead")
        
        if login_submitted and username and password:
            # Try to authenticate the user
            success, result = authenticate_user(conn, username, password)
            
            if success:
                # Set the user in session state
                st.session_state.user = result
                st.session_state.is_authenticated = True
                st.session_state.show_register = False
                st.toast(f"Welcome back, {result['username']}!", icon="👋")
                st.rerun()
            else:
                st.error(result)
        
        if show_register:
            st.session_state.show_register = True
            st.rerun()

def register_page():
    """Display the registration page"""
    st.subheader("Create a New Account")
    
    # Registration form
    with st.form("register_form"):
        username = st.text_input("Username", key="register_username")
        email = st.text_input("Email", key="register_email")
        full_name = st.text_input("Full Name (optional)", key="register_full_name")
        password = st.text_input("Password", type="password", key="register_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="confirm_password")
        
        col1, col2 = st.columns(2)
        register_submitted = col1.form_submit_button("Register")
        show_login = col2.form_submit_button("Login Instead")
        
        if register_submitted:
            # Validate the form
            if not username or not email or not password:
                st.error("Username, email, and password are required.")
            elif password != confirm_password:
                st.error("Passwords do not match.")
            else:
                # Try to create the user
                success, result = create_user(conn, username, email, password, full_name)
                
                if success:
                    # Set the user in session state
                    user_data = {
                        "id": result,
                        "username": username,
                        "email": email,
                        "full_name": full_name
                    }
                    st.session_state.user = user_data
                    st.session_state.is_authenticated = True
                    st.session_state.show_register = False
                    st.toast(f"Welcome, {username}! Your account has been created.", icon="✅")
                    st.rerun()
                else:
                    st.error(result)
        
        if show_login:
            st.session_state.show_register = False
            st.rerun()

# --- User Authentication Flow ---
# Initialize authentication state if not present
if "is_authenticated" not in st.session_state:
    st.session_state.is_authenticated = False

if "show_register" not in st.session_state:
    st.session_state.show_register = False
    
if "user" not in st.session_state:
    st.session_state.user = None

# Show the appropriate page based on authentication state
if not st.session_state.is_authenticated:
    # Logout button for the sidebar if previously logged in
    if st.session_state.user:
        with st.sidebar:
            if st.button("Logout", key="logout_button"):
                st.session_state.is_authenticated = False
                st.session_state.user = None
                st.toast("You have been logged out.")
                st.rerun()
    
    # Show login or registration page
    if st.session_state.show_register:
        register_page()
    else:
        login_page()
        
    # Stop the app here if not authenticated
    st.stop()

# --- Display user info in the sidebar ---
with st.sidebar:
    st.subheader(f"Welcome, {st.session_state.user['username']}!")
    if st.button("Logout", key="sidebar_logout"):
        st.session_state.is_authenticated = False
        st.session_state.user = None
        st.toast("You have been logged out.")
        st.rerun()

# ✅ Optional: View full database table
st.divider()
with st.expander("📅 Data stored in Dashboard table", expanded=False):
    with conn.session as session:
        stmt = sa.select(dashboard_table)
        result = session.execute(stmt)
        df = result.mappings().all()
        if df:
            df = pd.DataFrame(df)
            # Преобразуем все значения Enum в строку для Arrow
            if df['status'].apply(lambda x: hasattr(x, 'value')).any():
                df['status'] = df['status'].apply(lambda x: x.value if hasattr(x, 'value') else x)
            preferred_order = [
                'assignee_name', 'task_id', 'title', 'description', 'status', 
                'soft_deadline', 'hard_deadline', 'parent_task_id', 'created_at'
            ]
            df = df[[col for col in preferred_order if col in df.columns]]
            st.dataframe(df, use_container_width=True)
        else:
            st.info("The dashboard table is currently empty.")

SESSION_STATE_KEY_TASKS = "dashboard_data"

from enum import Enum

class TaskStatus(Enum):
    todo = "todo"
    in_progress = "in_progress"
    review = "review"
    done = "done"
    blocked = "blocked"
    cancelled = "cancelled"

@dataclass
class DashboardTask:
    id: int = None
    task_id: int = None
    title: str = ""
    description: str = ""
    assignee_id: int = None
    assignee_name: str = ""
    created_at: datetime = None
    status: str = "todo"
    soft_deadline: datetime = None
    hard_deadline: datetime = None
    parent_task_id: int = None

    @classmethod
    def from_row(cls, row):
        if row:
            return cls(**row._mapping)
        return None

def check_table_exists(connection: SQLConnection, table_name: str) -> bool:
    inspector = sa.inspect(connection.engine)
    return inspector.has_table(table_name)

def get_available_tasks(connection: SQLConnection, table: Table, current_user_id: str = None) -> Dict[int, str]:
    """Get all available tasks that can be selected as parent tasks"""
    # We'll filter by the current user if specified
    if current_user_id:
        stmt = sa.select(table).where(table.c.assignee_name == current_user_id)
    else:
        stmt = sa.select(table)
        
    with connection.session as session:
        result = session.execute(stmt)
        tasks = {}
        for row in result:
            if row.id and row.title:
                # Format status for display
                status = row.status
                if hasattr(status, 'value'):
                    status = status.value
                
                # Include more details for better identification
                tasks[row.task_id] = f"[{row.task_id}] {row.title} ({status})"
        return tasks

def load_all_tasks(connection: SQLConnection, table: Table) -> Dict[int, DashboardTask]:
    stmt = sa.select(table).where(table.c.assignee_name == st.session_state.user['username']).order_by(table.c.id)
    with connection.session as session:
        result = session.execute(stmt)
        tasks = [DashboardTask.from_row(row) for row in result.all()]
        return {task.task_id: task for task in tasks if task and task.title}

def create_task_callback(connection: SQLConnection, table: Table):
    if not st.session_state.new_task_form__title:
        st.toast("Title empty, not adding task")
        return
    unique_task_id = uuid.uuid4().int & 0x7FFFFFFF
    status_value = st.session_state.new_task_form__status
    
    # Handle parent task ID
    parent_task_id = st.session_state.new_task_form__parent_task_id
    if parent_task_id == "None":
        parent_task_id = unique_task_id
    else:
        try:
            parent_task_id = int(parent_task_id)
            
            # Verify parent task exists
            parent_task = load_all_tasks(connection, table)[parent_task_id]
            parent_task_id = parent_task.task_id
            if not parent_task:
                st.toast(f"Parent task with ID {parent_task_id} not found. Task created without parent.", icon="⚠️")
                parent_task_id = unique_task_id
        except ValueError:
            parent_task_id = unique_task_id
            
    new_task_data = {
        "task_id": unique_task_id,
        "title": st.session_state.new_task_form__title,
        "description": st.session_state.new_task_form__description,
        "assignee_id": st.session_state.user['id'],  # Use user ID from authenticated user
        "assignee_name": st.session_state.user['username'],  # Use username from authenticated user
        "created_at": datetime.now(),
        "status": status_value,
        "soft_deadline": st.session_state.new_task_form__soft_deadline,
        "hard_deadline": st.session_state.new_task_form__hard_deadline,
        "parent_task_id": parent_task_id,
    }
    stmt = table.insert().values(**new_task_data)
    with connection.session as session:
        result = session.execute(stmt)
        session.commit()
        task_id = result.inserted_primary_key[0]

    uploaded_file = st.session_state.get("new_task_form__file")
    if uploaded_file:
        documents_collection.insert_one({
            "task_id": task_id,
            "user_id": st.session_state.user['username'],  # Use username for MongoDB
            "filename": uploaded_file.name,
            "filedata": uploaded_file.read()
        })

    st.session_state[SESSION_STATE_KEY_TASKS] = load_all_tasks(conn, dashboard_table)

def open_update_callback(task_id: int):
    # Check if the task belongs to the current user before allowing edit
    task = load_all_tasks(conn, dashboard_table)[task_id]
    if task and task.assignee_name != st.session_state.user['username']:
        st.toast("You can only edit your own tasks.", icon="⚠️")
        return
    st.session_state[f"currently_editing__{task_id}"] = True

def cancel_update_callback(task_id: int):
    st.session_state[f"currently_editing__{task_id}"] = False

def update_task_callback(connection: SQLConnection, table: Table, task_id: int):
    status_value = st.session_state[f"edit_task_form_{task_id}__status"]
    # Handle parent task ID
    parent_task_id = st.session_state[f"edit_task_form_{task_id}__parent_task_id"]
    if parent_task_id == "None":
        parent_task_id = None
    else:
        try:
            parent_task_id = int(parent_task_id)
            
                
            # Verify parent task exists
            parent_task = load_all_tasks(connection, table)[parent_task_id]
            if parent_task:
                parent_task_id = parent_task.task_id
            else:
                st.toast(f"Parent task with ID {parent_task_id} not found. Task updated without parent.", icon="⚠️")
                parent_task_id = None
                
        except ValueError:
            parent_task_id = None
    updated_values = {
        "title": st.session_state[f"edit_task_form_{task_id}__title"],
        "description": st.session_state[f"edit_task_form_{task_id}__description"],
        "soft_deadline": st.session_state[f"edit_task_form_{task_id}__soft_deadline"],
        "hard_deadline": st.session_state[f"edit_task_form_{task_id}__hard_deadline"],
        "status": status_value,
        "parent_task_id": parent_task_id,
        "assignee_id": st.session_state.user['id'],  # Use authenticated user's ID
        "assignee_name": st.session_state.user['username'],  # Use authenticated user's username
    }
    if not updated_values["title"]:
        st.toast("Title cannot be empty.", icon="⚠️")
        st.session_state[f"currently_editing__{task_id}"] = True
        return
        
    # Check that this task belongs to the current user
    task = load_all_tasks(connection, table)[task_id]
    if task and task.assignee_name != st.session_state.user['username']:
        st.toast("You can only edit your own tasks.", icon="⚠️")
        st.session_state[f"currently_editing__{task_id}"] = False
        return
    stmt = table.update().where(table.c.task_id == task_id).values(**updated_values)
    with connection.session as session:
        session.execute(stmt)
        session.commit()
    st.session_state[SESSION_STATE_KEY_TASKS][task_id] = load_all_tasks(connection, table)[task_id]
    st.session_state[f"currently_editing__{task_id}"] = False

def delete_task_callback(connection: SQLConnection, table: Table, task_id: int):
    # Check that this task belongs to the current user
    task = load_all_tasks(connection, table)[task_id]
    if task and task.assignee_name != st.session_state.user['username']:
        st.toast("You can only delete your own tasks.", icon="⚠️")
        return
        
    # Check if this task has children
    with connection.session as session:
        stmt = sa.select(sa.func.count()).select_from(table).where((table.c.parent_task_id == task_id) & (table.c.task_id != table.c.parent_task_id))
        child_count = session.execute(stmt).scalar()
        
        if child_count > 0:
            st.toast(f"Cannot delete task with {child_count} child tasks. Please delete or reassign child tasks first.", icon="⚠️")
            return
    
    # Delete any associated documents
    documents_collection.delete_many({"task_id": task_id, "user_id": st.session_state.user['username']})
    
    # Delete the task
    stmt = table.delete().where(table.c.task_id == task_id)
    with connection.session as session:
        session.execute(stmt)
        session.commit()
        
    st.toast("Task deleted successfully.", icon="✅")
    st.session_state[SESSION_STATE_KEY_TASKS] = load_all_tasks(conn, dashboard_table)
    st.session_state[f"currently_editing__{task_id}"] = False

def task_card(connection: SQLConnection, table: Table, task_item: DashboardTask):
    task_id = task_item.task_id
    with st.container(border=True):
        display_title = task_item.title
        display_description = task_item.description or ":grey[*No description*]"
        status_value = task_item.status
        if isinstance(status_value, TaskStatus):
            status_value = status_value.value
        else:
            status_value = str(status_value)
            if status_value.startswith('TaskStatus.'):
                status_value = status_value.split('.', 1)[1]
        display_status = f":grey[Status: {status_value}]"
        display_soft_deadline = f":grey[Soft deadline: {task_item.soft_deadline.strftime('%Y-%m-%d') if task_item.soft_deadline else '-'}]"
        display_hard_deadline = f":grey[Hard deadline: {task_item.hard_deadline.strftime('%Y-%m-%d') if task_item.hard_deadline else '-'}]"
        display_task_id = f":grey[Task ID: {task_id}]"
        
        # Display parent task info if exists
        parent_task_info = ""
        if task_item.parent_task_id:
            parent_task = load_all_tasks(connection, table)[task_item.parent_task_id]
            if parent_task:
                parent_task_info = f":blue[↑ Parent task: {parent_task.title} (ID: {parent_task.task_id})]"
            else:
                parent_task_info = f":grey[No parent task]"
        
        # Find child tasks
        child_tasks_info = ""
        stmt = sa.select(table).where(table.c.parent_task_id == task_id)
        with connection.session as session:
            result = session.execute(stmt)
            child_tasks = result.all()
            if child_tasks:
                child_tasks_list = []
                for child in child_tasks:
                    child_tasks_list.append(f"{child.title} (ID: {child.task_id})")
                child_tasks_info = ":green[↓ Subtasks: " + ", ".join(child_tasks_list) + "]"
        
        st.subheader(display_title)
        st.markdown(display_description)
        task_col1, task_col2 = st.columns(2)
        task_col1.markdown(display_task_id)
        task_col1.markdown(display_status)
        task_col2.markdown(display_soft_deadline)
        task_col2.markdown(display_hard_deadline)
        
        # Display parent/child relationships
        if parent_task_info:
            st.markdown(parent_task_info)
        if child_tasks_info:
            st.markdown(child_tasks_info)
            
        # Use the authenticated user's username for document retrieval
        document = documents_collection.find_one({"task_id": task_id, "user_id": st.session_state.user['username']})
        if document:
            st.download_button(
                label=f"Download: {document['filename']}",
                data=document['filedata'],
                file_name=document['filename'],
                mime="application/octet-stream",
                use_container_width=True
            )
        edit_col, delete_col = st.columns(2)
        edit_col.button(
            "Edit",
            icon=":material/edit:",
            key=f"display_task_{task_id}__edit",
            on_click=open_update_callback,
            args=(task_id,),
            use_container_width=True,
        )
        if delete_col.button(
            "Delete",
            icon=":material/delete:",
            key=f"display_task_{task_id}__delete",
            use_container_width=True,
        ):
            delete_task_callback(connection, table, task_id)
            st.rerun(scope="app")

def task_edit_widget(connection: SQLConnection, table: Table, task_item: DashboardTask):
    task_id = task_item.task_id
    with st.form(f"edit_task_form_{task_id}"):
        st.text_input("Title", value=task_item.title, key=f"edit_task_form_{task_id}__title")
        st.text_area("Description", value=task_item.description, key=f"edit_task_form_{task_id}__description")
        status_values = [s.value for s in TaskStatus]
        if isinstance(task_item.status, TaskStatus):
            current_status = task_item.status.value
        else:
            current_status = str(task_item.status)
            if current_status.startswith('TaskStatus.'):
                current_status = current_status.split('.', 1)[1]
        st.selectbox("Status", status_values, index=status_values.index(current_status), key=f"edit_task_form_{task_id}__status")
        
        parent_task_options = {"None": "No parent task"}
        parent_task_options.update(available_tasks)
        
        # Select the current parent task if any
        current_parent = str(task_item.parent_task_id) if task_item.parent_task_id else "None"
        
        # Create a parent task dropdown
        st.selectbox(
            "Parent Task", 
            options=list(parent_task_options.keys()),
            format_func=lambda x: parent_task_options[x],
            key=f"edit_task_form_{task_id}__parent_task_id",
            index=list(parent_task_options.keys()).index(current_parent) if current_parent in parent_task_options else 0
        )
        
        st.date_input("Soft deadline", value=task_item.soft_deadline, key=f"edit_task_form_{task_id}__soft_deadline")
        st.date_input("Hard deadline", value=task_item.hard_deadline, key=f"edit_task_form_{task_id}__hard_deadline")
        
        st.markdown("**Note:** This will update the task as the current user.")
        
        submit_col, cancel_col = st.columns(2)
        if submit_col.form_submit_button(
            "Save",
            icon=":material/save:",
            type="primary",
            use_container_width=True,
        ):
            update_task_callback(connection, table, task_id)
            st.rerun(scope="app")
        cancel_col.form_submit_button(
            "Cancel",
            on_click=cancel_update_callback,
            args=(task_id,),
            use_container_width=True,
        )

@st.fragment
def task_component(_connection: SQLConnection, table: Table, task_id: int):
    task_item = st.session_state[SESSION_STATE_KEY_TASKS][task_id]
    currently_editing = st.session_state.get(f"currently_editing__{task_id}")
    # Verify the task belongs to the current user
    if task_item.assignee_name != st.session_state.user['username']:
        st.warning(f"Task {task_id} does not belong to you.")
        return
        
    if not currently_editing:
        task_card(_connection, table, task_item)
    else:
        task_edit_widget(_connection, table, task_item)

# --- Sidebar: Admin Options ---
with st.sidebar:
    st.header("Admin")
    
    # Only show admin options to admin users (you can define admins by username or role)
    is_admin = st.session_state.user['username'] in ['admin', 'root', 'superuser']
    
    if is_admin:
        with st.expander("Database Management"):
            # Create tables with form and submit button
            with st.form(key="create_tables_form"):
                st.write("Create or reset database tables")
                submit_button = st.form_submit_button(
                    "Create/Reset Tables", 
                    type="secondary",
                    use_container_width=True
                )
                
                if submit_button:
                    # Check if tables exist
                    inspector = sa.inspect(_connection.engine)
                    tables_exist = inspector.has_table(TABLE_NAME)
                    
                    # Create tables (SQLAlchemy will handle "IF NOT EXISTS" logic)
                    with _connection.session as session:
                        # Create metadata
                        if tables_exist:
                            # Drop existing tables if they exist
                            st.info("Dropping existing tables...")
                            dashboard_metadata.drop_all(_connection.engine)
                        
                        # Create tables
                        dashboard_metadata.create_all(_connection.engine)
                        session.commit()
                        st.toast("Dashboard tables created/reset successfully!", icon="✅")
        
        # User management section
        with st.expander("User Management"):
            # Show a list of all users
            with _connection.session as session:
                stmt = sa.text("SELECT id, username, email, full_name, created_at FROM users")
                result = session.execute(stmt)
                users = result.fetchall()
                
                if users:
                    user_df = pd.DataFrame(users)
                    st.dataframe(user_df, use_container_width=True)
                else:
                    st.info("No users found in the database.")
    
    st.divider()
    st.subheader("Session State Debug")
    st.json(st.session_state)

# --- Main App Flow ---
if not check_table_exists(conn, TABLE_NAME):
    st.warning("Create table from admin sidebar", icon="⚠")
    st.stop()

if SESSION_STATE_KEY_TASKS not in st.session_state:
    with st.spinner("Loading Tasks..."):
        st.session_state[SESSION_STATE_KEY_TASKS] = load_all_tasks(conn, dashboard_table)

current_tasks: Dict[int, DashboardTask] = st.session_state.get(SESSION_STATE_KEY_TASKS, {})
for task_id in current_tasks.keys():
    if f"currently_editing__{task_id}" not in st.session_state:
        st.session_state[f"currently_editing__{task_id}"] = False
    task_component(_connection=conn, table=dashboard_table, task_id=task_id)

with st.form("new_task_form", clear_on_submit=True):
    st.subheader(":material/add_circle: New task")
    st.text_input("Title", key="new_task_form__title", placeholder="Add your task")
    st.text_area("Description", key="new_task_form__description", placeholder="Add more details...")
    st.selectbox("Status", [s.value for s in TaskStatus], key="new_task_form__status")
    
    # Get available parent tasks
    available_tasks = get_available_tasks(conn, dashboard_table, st.session_state.user['username'])
    parent_task_options = {"None": "No parent task"}
    parent_task_options.update(available_tasks)
    
    # Create a parent task dropdown
    st.selectbox(
        "Parent Task", 
        options=list(parent_task_options.keys()),
        format_func=lambda x: parent_task_options[x],
        key="new_task_form__parent_task_id"
    )
    
    date_col1, date_col2, submit_col = st.columns((1, 1, 2), vertical_alignment="bottom")
    date_col1.date_input("Soft deadline", key="new_task_form__soft_deadline")
    date_col2.date_input("Hard deadline", key="new_task_form__hard_deadline")
    uploaded_file = st.file_uploader("Attach a file (optional)", key="new_task_form__file")
    submit_col.form_submit_button(
        "Add task",
        on_click=create_task_callback,
        args=(conn, dashboard_table),
        type="primary",
        use_container_width=True,
    )

st.markdown(
    "[![GitHub Badge](https://img.shields.io/badge/GitHub-181717?logo=github&logoColor=fff&style=flat)](https://github.com/kunal9960/streamlit_todo_list_app)&nbsp;&nbsp;" +
    "[![Streamlit Badge](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=fff&style=flat)](https://todo-list-app-kunal.streamlit.app/)")

ft = """
<style>
a:link , a:visited{
color: #BFBFBF;  /* theme's text color hex code at 75 percent brightness*/
background-color: transparent;
text-decoration: none;
}

a:hover,  a:active {
color: #0283C3; /* theme's primary color*/
background-color: transparent;
text-decoration: underline;
}

#page-container {
  position: relative;
  min-height: 10vh;
}

footer{
    visibility:hidden;
}

.footer {
position: relative;
left: 0;
top:150px;
bottom: 0;
width: 100%;
background-color: transparent;
color: #808080;
text-align: left;
}
</style>

<div id="page-container">

<div class="footer">
<p style='font-size: 1em;'>Made with <a style='display: inline; text-align: left;' href="https://streamlit.io/" target="_blank">Streamlit</a><br 'style= top:3px;'>
with <img src="https://em-content.zobj.net/source/skype/289/red-heart_2764-fe0f.png" alt="heart" height= "10"/><a style='display: inline; text-align: left;' href="https://github.com/kunal9960" target="_blank"> by Kunal</a>
<a style='display: inline; text-align: left;'>© Copyright 2025</a></p>
</div>

</div>
"""
st.write(ft, unsafe_allow_html=True)