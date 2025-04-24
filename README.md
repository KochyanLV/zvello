# Database Todo App 📝

This project creates a multi-user **Todo Dashboard** using **Python, Streamlit, and SQLAlchemy**, with all data stored and retrieved from a **SQL database**. Users can manage their daily tasks through an intuitive UI with persistent backend support.

<img src="https://github.com/KochyanLV/zvello/blob/master/Main%20Page.jpg?raw=true" width="800">
<img src="https://github.com/KochyanLV/zvello/blob/master/Database.png?raw=true" width="800">

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

1. **Make venv:**

    ```commandline
    python3 -m venv venv
    source venv/bin/activate
    ```

2. **Install required packages:**

    ```commandline
    pip install -r requirements.txt
    ```

3. **Run the Streamlit app:**

   ```commandline
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
