# Database Todo App 📝

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://todo-list-app-kunal.streamlit.app/)
[![Project Status: Active](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active)
![uptime](https://img.shields.io/badge/uptime-100%25-brightgreen)
[![Made With Love](https://img.shields.io/badge/Made%20With-Love-orange.svg)](https://github.com/kunal9960)

This project creates a multi-user **Todo Dashboard** using **Python, Streamlit, and SQLAlchemy**, with all data stored and retrieved from a **SQL database**. Users can manage their daily tasks through an intuitive UI with persistent backend support.

<img src="https://github.com/kunal9960/streamlit_todo_list_app/blob/master/Main%20Page.jpg?raw=true" width="800">
<img src="https://github.com/kunal9960/streamlit_todo_list_app/blob/master/Database.png?raw=true" width="800">

---

## Features

- Multi-user support with session-based identification.
- Add, edit, mark done, and delete todos.
- Set due dates and manage long-term tasks.
- View all data stored in the SQL database.
- Admin tools for table creation and debugging.

---

## Requirements

Install using  ```requirements.txt```
- Python 3.11 or higher
- Streamlit
- SQLAlchemy
- pandas

---

## Setup

1. **Install required packages:**

    ```bash
    pip install -r requirements.txt
    ```

2. **Configure your database connection:**

- Set up your database (SQLite, PostgreSQL, etc.).
- Define your connection in .streamlit/secrets.toml as:
- [connections.todo_db]
```url = "sqlite:///todo.db"  # Or your actual database URL```

3. **Run the Streamlit app:**
   ```bash
   streamlit run main.py
   ```

---

## Usage

1. **User Identification:**
Prompt appears once per session to enter your name for personalized todos.

2. **Todo Management:**
Create new tasks with a title, optional description, and due date. Tasks can be marked as done or edited later.

3. **Database View:**
Expand the table viewer to see all your tasks directly from the SQL database.

4. **Admin Tools:**
Sidebar provides debug information and a button to create tables if needed.

---

## Contributing

Contributions are welcome! If you have any ideas for improvements or new features, feel free to fork the repository and submit a pull request. You can also open an issue to report bugs or suggest enhancements.

---

## Acknowledgments

Feel free to contact me if you need help with any of the projects :)
