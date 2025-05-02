from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, Optional
import sqlalchemy as sa
import streamlit as st
from sqlalchemy import Boolean, Column, Date, Integer, MetaData, String, Table
from streamlit.connections import SQLConnection
import pandas as pd
import uuid

# --- MongoDB setup ---
from pymongo.mongo_client import MongoClient
import certifi

uri = "mongodb+srv://kochyanlv:qwerty12345@cluster71234.ifyaey3.mongodb.net/?retryWrites=true&w=majority&appName=Cluster71234"
mongo_client = MongoClient(uri, tlsCAFile=certifi.where())
mongo_db = mongo_client["todo_db"]
documents_collection = mongo_db["documents"]


st.set_page_config(
    page_title="Todo List App",
    page_icon="🎯",
    initial_sidebar_state="collapsed",
)

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


# --- Ask for user's name once per session ---
if "user_id" not in st.session_state or not st.session_state.user_id:
    st.session_state.user_id = st.text_input("Enter your name to start:", key="user_input")
    if not st.session_state.user_id:
        st.stop()

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
                tasks[row.id] = f"[{row.task_id}] {row.title} ({status})"
        return tasks

def load_all_tasks(connection: SQLConnection, table: Table) -> Dict[int, DashboardTask]:
    stmt = sa.select(table).where(table.c.assignee_name == st.session_state.user_id).order_by(table.c.id)
    with connection.session as session:
        result = session.execute(stmt)
        tasks = [DashboardTask.from_row(row) for row in result.all()]
        return {task.id: task for task in tasks if task and task.title}

def load_task(connection: SQLConnection, table: Table, task_id: int) -> Optional[DashboardTask]:
    stmt = sa.select(table).where(table.c.id == task_id)
    with connection.session as session:
        result = session.execute(stmt)
        row = result.first()
        return DashboardTask.from_row(row)

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
            parent_task = load_task(connection, table, parent_task_id)
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
        "assignee_id": None,
        "assignee_name": st.session_state.user_id,
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
            "user_id": st.session_state.user_id,
            "filename": uploaded_file.name,
            "filedata": uploaded_file.read()
        })

    st.session_state[SESSION_STATE_KEY_TASKS] = load_all_tasks(conn, dashboard_table)

def open_update_callback(task_id: int):
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
            
            # Prevent circular dependencies and self-references
            if parent_task_id == task_id:
                st.toast("A task cannot be its own parent.", icon="⚠️")
                st.session_state[f"currently_editing__{task_id}"] = True
                return
                
            # Check for deeper circular dependencies
            def check_for_circular_dependency(check_parent_id, original_task_id, visited=None):
                if visited is None:
                    visited = set()
                
                if check_parent_id in visited:
                    return True  # Circular dependency found
                
                if check_parent_id is None:
                    return False  # No parent, so no circular dependency
                
                visited.add(check_parent_id)
                
                # Get the parent's parent
                with connection.session as session:
                    stmt = sa.select(table.c.parent_task_id).where(table.c.id == check_parent_id)
                    result = session.execute(stmt).first()
                    
                    if result and result[0]:
                        grand_parent_id = result[0]
                        # Check if this would create a circular reference
                        if grand_parent_id == original_task_id:
                            return True
                        return check_for_circular_dependency(grand_parent_id, original_task_id, visited)
                    
                return False
            
            if check_for_circular_dependency(parent_task_id, task_id):
                st.toast("This would create a circular dependency between tasks.", icon="⚠️")
                st.session_state[f"currently_editing__{task_id}"] = True
                return
                
            # Verify parent task exists
            parent_task = load_task(connection, table, parent_task_id)
            if not parent_task:
                st.toast(f"Parent task with ID {parent_task_id} not found. Task updated without parent.", icon="⚠️")
                parent_task_id = None
            parent_task_id = parent_task.task_id
                
        except ValueError:
            parent_task_id = None
    
    updated_values = {
        "title": st.session_state[f"edit_task_form_{task_id}__title"],
        "description": st.session_state[f"edit_task_form_{task_id}__description"],
        "soft_deadline": st.session_state[f"edit_task_form_{task_id}__soft_deadline"],
        "hard_deadline": st.session_state[f"edit_task_form_{task_id}__hard_deadline"],
        "status": status_value,
        "parent_task_id": parent_task_id,
    }
    if not updated_values["title"]:
        st.toast("Title cannot be empty.", icon="⚠️")
        st.session_state[f"currently_editing__{task_id}"] = True
        return
    stmt = table.update().where(table.c.id == task_id).values(**updated_values)
    with connection.session as session:
        session.execute(stmt)
        session.commit()
    st.session_state[SESSION_STATE_KEY_TASKS][task_id] = load_task(connection, table, task_id)
    st.session_state[f"currently_editing__{task_id}"] = False

def delete_task_callback(connection: SQLConnection, table: Table, task_id: int):
    stmt = table.delete().where(table.c.id == task_id)
    with connection.session as session:
        session.execute(stmt)
        session.commit()
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
            parent_task = load_task(connection, table, task_item.parent_task_id)
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
            
        document = documents_collection.find_one({"task_id": task_id, "user_id": st.session_state.user_id})
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
        
        # Get available parent tasks (excluding this task)
        available_tasks = get_available_tasks(connection, table, st.session_state.user_id)
        if task_id in available_tasks:
            del available_tasks[task_id]  # Can't select self as parent
            
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
        submit_col, cancel_col = st.columns(2)
        submit_col.form_submit_button(
            "Save",
            icon=":material/save:",
            type="primary",
            on_click=update_task_callback,
            args=(connection, table, task_id),
            use_container_width=True,
        )
        cancel_col.form_submit_button(
            "Cancel",
            on_click=cancel_update_callback,
            args=(task_id,),
            use_container_width=True,
        )

@st.fragment
def task_component(connection: SQLConnection, table: Table, task_id: int):
    task_item = st.session_state[SESSION_STATE_KEY_TASKS][task_id]
    currently_editing = st.session_state.get(f"currently_editing__{task_id}", False)
    if not currently_editing:
        task_card(connection, table, task_item)
    else:
        task_edit_widget(connection, table, task_item)

# --- Sidebar: Admin Options ---
with st.sidebar:
    st.header("Admin")
    
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
            inspector = sa.inspect(conn.engine)
            tables_exist = inspector.has_table(TABLE_NAME)
            
            # Create tables (SQLAlchemy will handle "IF NOT EXISTS" logic)
            with conn.session as session:
                # Create metadata
                if tables_exist:
                    # Drop existing tables if they exist
                    st.info("Dropping existing tables...")
                    dashboard_metadata.drop_all(conn.engine)
                
                # Create tables
                dashboard_metadata.create_all(conn.engine)
                session.commit()
                st.toast("Dashboard tables created/reset successfully!", icon="✅")
    
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
    task_component(conn, dashboard_table, task_id)

with st.form("new_task_form", clear_on_submit=True):
    st.subheader(":material/add_circle: New task")
    st.text_input("Title", key="new_task_form__title", placeholder="Add your task")
    st.text_area("Description", key="new_task_form__description", placeholder="Add more details...")
    st.selectbox("Status", [s.value for s in TaskStatus], key="new_task_form__status")
    
    # Get available parent tasks
    available_tasks = get_available_tasks(conn, dashboard_table, st.session_state.user_id)
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