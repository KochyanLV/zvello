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
                'assignee_name', 'task_id', 'title', 'description', 'status', 'soft_deadline', 'hard_deadline', 'created_at'
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

    @classmethod
    def from_row(cls, row):
        if row:
            return cls(**row._mapping)
        return None

def check_table_exists(connection: SQLConnection, table_name: str) -> bool:
    inspector = sa.inspect(connection.engine)
    return inspector.has_table(table_name)

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
    updated_values = {
        "title": st.session_state[f"edit_task_form_{task_id}__title"],
        "description": st.session_state[f"edit_task_form_{task_id}__description"],
        "soft_deadline": st.session_state[f"edit_task_form_{task_id}__soft_deadline"],
        "hard_deadline": st.session_state[f"edit_task_form_{task_id}__hard_deadline"],
        "status": status_value,
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
    task_id = task_item.id
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
        display_task_id = f":grey[task_id: {task_item.task_id}]"
        st.subheader(display_title)
        st.markdown(display_description)
        st.markdown(display_task_id)
        st.markdown(display_status)
        st.markdown(display_soft_deadline)
        st.markdown(display_hard_deadline)
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
    task_id = task_item.id
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
    if st.button("Create table", type="secondary"):
        st.toast("Dashboard table created successfully!", icon="✅")
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