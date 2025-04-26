from dataclasses import dataclass
from datetime import date
from typing import Dict, Optional
import sqlalchemy as sa
import streamlit as st
from sqlalchemy import Boolean, Column, Date, Integer, MetaData, String, Table
from streamlit.connections import SQLConnection
import pandas as pd

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
TABLE_NAME = "todo"
conn = st.connection("todo_db", ttl=5 * 60)

@st.cache_resource
def connect_table():
    metadata_obj = MetaData()
    todo_table = Table(
        TABLE_NAME,
        metadata_obj,
        Column("id", Integer, primary_key=True),
        Column("user_id", String, nullable=True),
        Column("title", String(30)),
        Column("description", String, nullable=True),
        Column("created_at", Date),
        Column("due_at", Date, nullable=True),
        Column("done", Boolean, nullable=True),
    )
    return metadata_obj, todo_table

metadata_obj, todo_table = connect_table()

# ✅ Optional: View full database table
st.divider()
with st.expander("📅 Data stored in Todo table", expanded=False):
    with conn.session as session:
        stmt = sa.select(todo_table)
        result = session.execute(stmt)
        df = result.mappings().all()
        if df:
            df = pd.DataFrame(df)
            # Reorder columns: user_id (name) first, created_at last
            preferred_order = ['user_id', 'title', 'description', 'due_at', 'done', 'created_at']
            df = df[[col for col in preferred_order if col in df.columns]]
            st.dataframe(df, use_container_width=True)
        else:
            st.info("The todo table is currently empty.")


# --- Ask for user's name once per session ---
if "user_id" not in st.session_state or not st.session_state.user_id:
    st.session_state.user_id = st.text_input("Enter your name to start:", key="user_input")
    if not st.session_state.user_id:
        st.stop()

SESSION_STATE_KEY_TODOS = "todos_data"

@dataclass
class Todo:
    id: Optional[int] = None
    user_id: Optional[str] = None
    title: str = ""
    description: Optional[str] = None
    created_at: Optional[date] = None
    due_at: Optional[date] = None
    done: bool = False

    @classmethod
    def from_row(cls, row):
        if row:
            return cls(**row._mapping)
        return None

def check_table_exists(connection: SQLConnection, table_name: str) -> bool:
    inspector = sa.inspect(connection.engine)
    return inspector.has_table(table_name)

def load_all_todos(connection: SQLConnection, table: Table) -> Dict[int, Todo]:
    stmt = sa.select(table).where(table.c.user_id == st.session_state.user_id).order_by(table.c.id)
    with connection.session as session:
        result = session.execute(stmt)
        todos = [Todo.from_row(row) for row in result.all()]
        return {todo.id: todo for todo in todos if todo and todo.title}

def load_todo(connection: SQLConnection, table: Table, todo_id: int) -> Optional[Todo]:
    stmt = sa.select(table).where(table.c.id == todo_id)
    with connection.session as session:
        result = session.execute(stmt)
        row = result.first()
        return Todo.from_row(row)

def create_todo_callback(connection: SQLConnection, table: Table):
    if not st.session_state.new_todo_form__title:
        st.toast("Title empty, not adding todo")
        return
    new_todo_data = {
        "user_id": st.session_state.user_id,
        "title": st.session_state.new_todo_form__title,
        "description": st.session_state.new_todo_form__description,
        "created_at": date.today(),
        "due_at": st.session_state.new_todo_form__due_date,
        "done": False,
    }
    stmt = table.insert().values(**new_todo_data)
    with connection.session as session:
        session.execute(stmt)
        session.commit()
    st.session_state[SESSION_STATE_KEY_TODOS] = load_all_todos(conn, todo_table)

def open_update_callback(todo_id: int):
    st.session_state[f"currently_editing__{todo_id}"] = True

def cancel_update_callback(todo_id: int):
    st.session_state[f"currently_editing__{todo_id}"] = False

def update_todo_callback(connection: SQLConnection, table: Table, todo_id: int):
    updated_values = {
        "title": st.session_state[f"edit_todo_form_{todo_id}__title"],
        "description": st.session_state[f"edit_todo_form_{todo_id}__description"],
        "due_at": st.session_state[f"edit_todo_form_{todo_id}__due_date"],
    }
    if not updated_values["title"]:
        st.toast("Title cannot be empty.", icon="⚠️")
        st.session_state[f"currently_editing__{todo_id}"] = True
        return
    stmt = table.update().where(table.c.id == todo_id).values(**updated_values)
    with connection.session as session:
        session.execute(stmt)
        session.commit()
    st.session_state[SESSION_STATE_KEY_TODOS][todo_id] = load_todo(connection, table, todo_id)
    st.session_state[f"currently_editing__{todo_id}"] = False

def delete_todo_callback(connection: SQLConnection, table: Table, todo_id: int):
    stmt = table.delete().where(table.c.id == todo_id)
    with connection.session as session:
        session.execute(stmt)
        session.commit()
    st.session_state[SESSION_STATE_KEY_TODOS] = load_all_todos(conn, todo_table)
    st.session_state[f"currently_editing__{todo_id}"] = False

def mark_done_callback(connection: SQLConnection, table: Table, todo_id: int):
    current_done_status = st.session_state[SESSION_STATE_KEY_TODOS][todo_id].done
    stmt = table.update().where(table.c.id == todo_id).values(done=not current_done_status)
    with connection.session as session:
        session.execute(stmt)
        session.commit()
    st.session_state[SESSION_STATE_KEY_TODOS][todo_id] = load_todo(connection, table, todo_id)

def todo_card(connection: SQLConnection, table: Table, todo_item: Todo):
    todo_id = todo_item.id
    with st.container(border=True):
        display_title = todo_item.title
        display_description = todo_item.description or ":grey[*No description*]"
        display_due_date = f":grey[Due {todo_item.due_at.strftime('%Y-%m-%d')}]"
        if todo_item.done:
            strikethrough = "~~"
            display_title = f"{strikethrough}{display_title}{strikethrough}"
            display_description = f"{strikethrough}{display_description}{strikethrough}"
            display_due_date = f"{strikethrough}{display_due_date}{strikethrough}"
        st.subheader(display_title)
        st.markdown(display_description)
        st.markdown(display_due_date)
        done_col, edit_col, delete_col = st.columns(3)
        done_col.button(
            "Done" if not todo_item.done else "Redo",
            icon=":material/check_circle:",
            key=f"display_todo_{todo_id}__done",
            on_click=mark_done_callback,
            args=(conn, todo_table, todo_id),
            type="secondary" if todo_item.done else "primary",
            use_container_width=True,
        )
        edit_col.button(
            "Edit",
            icon=":material/edit:",
            key=f"display_todo_{todo_id}__edit",
            on_click=open_update_callback,
            args=(todo_id,),
            disabled=todo_item.done,
            use_container_width=True,
        )
        if delete_col.button(
            "Delete",
            icon=":material/delete:",
            key=f"display_todo_{todo_id}__delete",
            use_container_width=True,
        ):
            delete_todo_callback(connection, table, todo_id)
            st.rerun(scope="app")

def todo_edit_widget(connection: SQLConnection, table: Table, todo_item: Todo):
    todo_id = todo_item.id
    with st.form(f"edit_todo_form_{todo_id}"):
        st.text_input("Title", value=todo_item.title, key=f"edit_todo_form_{todo_id}__title")
        st.text_area("Description", value=todo_item.description, key=f"edit_todo_form_{todo_id}__description")
        st.date_input("Due date", value=todo_item.due_at, key=f"edit_todo_form_{todo_id}__due_date")
        submit_col, cancel_col = st.columns(2)
        submit_col.form_submit_button(
            "Save",
            icon=":material/save:",
            type="primary",
            on_click=update_todo_callback,
            args=(connection, table, todo_id),
            use_container_width=True,
        )
        cancel_col.form_submit_button(
            "Cancel",
            on_click=cancel_update_callback,
            args=(todo_id,),
            use_container_width=True,
        )

@st.fragment
def todo_component(connection: SQLConnection, table: Table, todo_id: int):
    todo_item = st.session_state[SESSION_STATE_KEY_TODOS][todo_id]
    currently_editing = st.session_state.get(f"currently_editing__{todo_id}", False)
    if not currently_editing:
        todo_card(connection, table, todo_item)
    else:
        todo_edit_widget(connection, table, todo_item)

# --- Sidebar: Admin Options ---
with st.sidebar:
    st.header("Admin")
    if st.button("Create table", type="secondary"):
        st.toast("Todo table created successfully!", icon="✅")
    st.divider()
    st.subheader("Session State Debug")
    st.json(st.session_state)

# --- Main App Flow ---
if not check_table_exists(conn, TABLE_NAME):
    st.warning("Create table from admin sidebar", icon="⚠")
    st.stop()

if SESSION_STATE_KEY_TODOS not in st.session_state:
    with st.spinner("Loading Todos..."):
        st.session_state[SESSION_STATE_KEY_TODOS] = load_all_todos(conn, todo_table)

current_todos: Dict[int, Todo] = st.session_state.get(SESSION_STATE_KEY_TODOS, {})
for todo_id in current_todos.keys():
    if f"currently_editing__{todo_id}" not in st.session_state:
        st.session_state[f"currently_editing__{todo_id}"] = False
    todo_component(conn, todo_table, todo_id)

with st.form("new_todo_form", clear_on_submit=True):
    st.subheader(":material/add_circle: New todo")
    st.text_input("Title", key="new_todo_form__title", placeholder="Add your task")
    st.text_area("Description", key="new_todo_form__description", placeholder="Add more details...")
    date_col, submit_col = st.columns((1, 2), vertical_alignment="bottom")
    date_col.date_input("Due date", key="new_todo_form__due_date")
    submit_col.form_submit_button(
        "Add todo",
        on_click=create_todo_callback,
        args=(conn, todo_table),
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