# app.py - Updated Streamlit Web App for CSES Project Management
# Run with: streamlit run app.py

import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3
import os
from functools import lru_cache  # For caching to speed up

# Create photos folder if not exists
os.makedirs("photos", exist_ok=True)

# Database functions (your original + updates)

DB_NAME = "project_manager.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Companies (unchanged)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)

    # Company representatives (unchanged)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS company_representatives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            position TEXT
        )
    """)

    # Employees (base table)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            active INTEGER DEFAULT 1
        )
    """)

    # Migrate employees: Add role and pin if not exist
    try:
        cur.execute("ALTER TABLE employees ADD COLUMN role TEXT DEFAULT 'site'")
    except sqlite3.OperationalError:
        pass  # Column already exists
    try:
        cur.execute("ALTER TABLE employees ADD COLUMN pin TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Projects (unchanged)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            quote_number TEXT,
            project_number TEXT,
            representative_id INTEGER,
            owner_user TEXT NOT NULL,
            progress REAL DEFAULT 0,
            archived INTEGER DEFAULT 0
        )
    """)

    # Tasks (base table)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            area TEXT,
            equipment TEXT,
            kw REAL,
            main_task TEXT,
            sub_task TEXT,
            assigned_to INTEGER,
            due_date TEXT,
            completed INTEGER DEFAULT 0,
            completed_date TEXT,
            archived INTEGER DEFAULT 0
        )
    """)

    # Migrate tasks: Add comments and photo_path if not exist
    try:
        cur.execute("ALTER TABLE tasks ADD COLUMN comments TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("ALTER TABLE tasks ADD COLUMN photo_path TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

    # Seed management employees if not exist (hardcoded PINs - change them!)
    add_employee("Jaco Kotze", role="management", pin="1234")
    add_employee("Craig Brooks", role="management", pin="5678")

# ---------------- COMPANIES ---------------- (unchanged)

def add_company(name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO companies (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()


@lru_cache(maxsize=32)
def get_companies():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM companies ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return rows


# ---------------- REPRESENTATIVES ---------------- (unchanged)

def get_company_representatives(company_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, position FROM company_representatives WHERE company_id=?",
        (company_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def add_company_representative(company_id, name, position):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO company_representatives (company_id, name, position) VALUES (?, ?, ?)",
        (company_id, name, position)
    )
    conn.commit()
    conn.close()


# ---------------- EMPLOYEES ---------------- (updated with role/pin)

def add_employee(name, role='site', pin=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO employees (name, role, pin) VALUES (?, ?, ?)",
        (name, role, pin)
    )
    conn.commit()
    conn.close()


@lru_cache(maxsize=32)
def get_employees():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, role, pin FROM employees WHERE active=1 ORDER BY name"
    )
    rows = cur.fetchall()
    conn.close()
    return rows


# ---------------- PROJECTS ---------------- (unchanged)

def add_project(company_id, name, description, quote_number,
                project_number, representative_id, owner_user):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO projects (
            company_id, name, description, quote_number,
            project_number, representative_id, owner_user
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        company_id, name, description, quote_number,
        project_number, representative_id, owner_user
    ))
    conn.commit()
    conn.close()


@lru_cache(maxsize=32)
def get_projects_by_company(company_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, progress, owner_user
        FROM projects
        WHERE company_id=? AND archived=0
        ORDER BY name
    """, (company_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def recalc_project_progress(project_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*), SUM(completed)
        FROM tasks
        WHERE project_id=? AND archived=0
    """, (project_id,))
    total, done = cur.fetchone()

    progress = 0
    if total and total > 0:
        progress = (done or 0) / total * 100

    cur.execute(
        "UPDATE projects SET progress=? WHERE id=?",
        (progress, project_id)
    )

    conn.commit()
    conn.close()


# ---------------- TASKS ---------------- (updated with comments/photo)

def insert_task(project_id, area, equipment, kw,
                main_task, sub_task, assigned_to, due_date, comments='', photo_path=''):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO tasks (
            project_id, area, equipment, kw,
            main_task, sub_task, assigned_to, due_date, comments, photo_path
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        project_id, area, equipment, kw,
        main_task, sub_task, assigned_to, due_date, comments, photo_path
    ))
    conn.commit()
    conn.close()


def get_project_tasks(project_id, user_id=None, is_management=False):
    conn = get_connection()
    cur = conn.cursor()
    sql = """
        SELECT
            t.id,
            t.area,
            t.equipment,
            t.main_task,
            t.sub_task,
            t.due_date,
            t.completed,
            t.completed_date,
            e.name AS assigned_to,
            t.comments,
            t.photo_path
        FROM tasks t
        LEFT JOIN employees e ON t.assigned_to = e.id
        WHERE t.project_id=? AND t.archived=0
    """
    params = [project_id]
    if not is_management:
        sql += " AND t.assigned_to = ?"
        params.append(user_id)
    sql += " ORDER BY t.due_date"
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return rows


def toggle_task_completed(task_id, completed):
    conn = get_connection()
    cur = conn.cursor()

    completed_date = None
    if completed:
        completed_date = datetime.now().strftime("%Y-%m-%d")

    cur.execute("""
        UPDATE tasks
        SET completed=?, completed_date=?
        WHERE id=?
    """, (int(completed), completed_date, task_id))

    conn.commit()
    conn.close()

def update_task_comments(task_id, comments):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET comments=? WHERE id=?", (comments, task_id))
    conn.commit()
    conn.close()

def update_task_photo(task_id, photo_path):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET photo_path=? WHERE id=?", (photo_path, task_id))
    conn.commit()
    conn.close()

def update_task_due_date(task_id, due_date):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET due_date=? WHERE id=?", (due_date, task_id))
    conn.commit()
    conn.close()

def get_task_schedule(user_id=None, is_management=False, target_date=None):
    conn = get_connection()
    cur = conn.cursor()

    sql = """
    SELECT
        t.id,
        t.due_date,
        e.name AS employee,
        c.name AS company,
        p.name AS project,
        t.area,
        t.equipment,
        t.main_task,
        t.sub_task
    FROM tasks t
    JOIN projects p ON t.project_id = p.id
    JOIN companies c ON p.company_id = c.id
    LEFT JOIN employees e ON t.assigned_to = e.id
    WHERE t.completed = 0
    """
    params = []
    if not is_management:
        sql += " AND t.assigned_to = ?"
        params.append(user_id)
    if target_date:
        sql += " AND t.due_date = ?"
        params.append(target_date)

    sql += " ORDER BY t.due_date ASC"

    cur.execute(sql, params)
    rows = cur.fetchall()

    conn.close()
    return rows

init_db()

# Helper to get employee ID from name
def employee_id_from_name(name):
    employees = get_employees()
    for eid, ename, _, _ in employees:
        if ename == name:
            return eid
    return None

# Helper to get role and PIN from name
def get_employee_details(name):
    employees = get_employees()
    for eid, ename, role, pin in employees:
        if ename == name:
            return eid, role, pin
    return None, None, None

# --- Streamlit App Structure ---
st.set_page_config(page_title="CSES Project Management", layout="wide")

# Session state
if "user" not in st.session_state:
    st.session_state.user = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "role" not in st.session_state:
    st.session_state.role = None
if "company_id" not in st.session_state:
    st.session_state.company_id = None
if "project_id" not in st.session_state:
    st.session_state.project_id = None

# --- Login Page ---
def login_page():
    st.title("Login - CSES Project Management")
    
    users = [name for _, name, _, _ in get_employees()]
    if not users:
        users = ["admin"]
    user = st.selectbox("Select User", users)
    pin = st.text_input("Enter PIN", type="password")
    
    if st.button("Login"):
        if user and pin:
            eid, role, stored_pin = get_employee_details(user)
            if pin == stored_pin:
                st.session_state.user = user
                st.session_state.user_id = eid
                st.session_state.role = role
                st.rerun()
            else:
                st.error("Invalid PIN")
        else:
            st.error("Select user and enter PIN")

# --- Main App ---
def main_app():
    is_management = st.session_state.role == 'management'
    
    # Logo
    if os.path.exists("CSES Logo.png"):
        st.image("CSES Logo.png", width=200)
    
    st.title(f"CSES Project Management - Welcome, {st.session_state.user}")
    
    # Sidebar Navigation
    with st.sidebar:
        st.header("Navigation")
        if st.button("Logout"):
            st.session_state.user = None
            st.session_state.user_id = None
            st.session_state.role = None
            st.rerun()
        
        st.subheader("Companies")
        companies = get_companies()
        company_names = [name for _, name in companies]
        selected_company = st.selectbox("Select Company", company_names)
        if selected_company:
            st.session_state.company_id = next(id for id, name in companies if name == selected_company)
        
        if is_management:
            new_company = st.text_input("New Company Name")
            if st.button("Add Company"):
                if new_company:
                    add_company(new_company)
                    st.success("Company added!")
                    st.rerun()
        
        if st.session_state.company_id:
            st.subheader("Projects")
            projects = get_projects_by_company(st.session_state.company_id)
            project_names = [name for _, name, _, _ in projects]
            selected_project = st.selectbox("Select Project", project_names)
            if selected_project:
                st.session_state.project_id = next(id for id, name, _, _ in projects if name == selected_project)
        
            if is_management:
                with st.expander("Add New Project"):
                    proj_name = st.text_input("Project Name")
                    desc = st.text_area("Description")
                    quote_num = st.text_input("Quote Number")
                    proj_num = st.text_input("Project Number")
                    rep_id = st.number_input("Representative ID", min_value=0)
                    owner = st.session_state.user
                    if st.button("Add Project"):
                        add_project(st.session_state.company_id, proj_name, desc, quote_num, proj_num, rep_id, owner)
                        st.success("Project added!")
                        st.rerun()
        
        st.subheader("Quick Actions")
        if is_management and st.button("Manage Employees"):
            new_emp = st.text_input("New Employee Name")
            new_role = st.selectbox("Role", ["management", "site"])
            new_pin = st.text_input("PIN (4 digits)", type="password")
            if st.button("Add"):
                if new_emp and new_pin:
                    add_employee(new_emp, role=new_role, pin=new_pin)
                    st.success("Employee added!")
                    st.rerun()

    # Main Content Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Scope Builder", "Active Tasks", "My Tasks", "Schedule"])

    with tab1:
        scope_builder(is_management)

    with tab2:
        active_tasks(is_management)

    with tab3:
        my_tasks()

    with tab4:
        task_schedule(is_management)

# --- Scope Builder Tab ---
def scope_builder(is_management):
    if not st.session_state.project_id:
        st.info("Select a project first.")
        return
    
    st.header("Scope Builder")
    
    MAIN_TASKS = {
        "NH3 System": ["Install Cable Ladder", "Install DB", "Terminate DB", "Commissioning"],
        "Pump": ["Install Cable Ladder", "Install Motor", "Terminate Motor", "Test Run"],
        "Fan": ["Install Cable Ladder", "Install Fan", "Terminate Fan", "Test Run"],
        "Compressor": ["Install Cable Ladder", "Install Compressor", "Terminate", "Commissioning"],
    }
    DEFAULT_AREAS = ["Plant Room", "Roof", "Cold Room", "MCC Room"]
    
    if is_management:
        with st.expander("Add New Scope Item"):
            area = st.selectbox("Area", DEFAULT_AREAS)
            main_task = st.selectbox("Main Task / System", list(MAIN_TASKS.keys()))
            equipment = st.text_input("Equipment")
            sub_task = st.selectbox("Sub Task", MAIN_TASKS.get(main_task, []))
            kw = st.number_input("kW", min_value=0.0)
            employee = st.selectbox("Employee", [name for _, name, _, _ in get_employees()])
            due_date = st.date_input("Due Date")
            
            if st.button("Add Task"):
                assigned_id = employee_id_from_name(employee)
                if assigned_id is None:
                    st.error("Employee not found.")
                    return
                insert_task(
                    st.session_state.project_id, area, equipment, kw,
                    main_task, sub_task, assigned_id, due_date.strftime("%Y-%m-%d")
                )
                st.success("Task added!")
                recalc_project_progress(st.session_state.project_id)

    # Display tasks (filtered)
    tasks = get_project_tasks(st.session_state.project_id, st.session_state.user_id, is_management)
    if tasks:
        df = pd.DataFrame(tasks, columns=["ID", "Area", "Equipment", "Main Task", "Sub Task", "Due Date", "Completed", "Completed Date", "Assigned To", "Comments", "Photo"])
        st.dataframe(df)

# --- Active Tasks Tab ---
def active_tasks(is_management):
    if not st.session_state.project_id:
        st.info("Select a project first.")
        return
    
    st.header("Active Tasks")
    tasks = get_project_tasks(st.session_state.project_id, st.session_state.user_id, is_management)
    
    for task in tasks:
        tid, area, equip, main, sub, due, comp, cdate, assigned, comments, photo_path = task
        with st.expander(f"{area} – {main} / {sub} | Due: {due} | Assigned: {assigned}"):
            completed = st.checkbox("Completed", value=bool(comp), key=f"comp_{tid}")
            if completed != bool(comp):
                toggle_task_completed(tid, completed)
                st.rerun()
            
            new_comments = st.text_area("Comments", value=comments or "", key=f"comments_{tid}")
            if new_comments != (comments or ""):
                update_task_comments(tid, new_comments)
                st.rerun()
            
            if photo_path:
                st.image(photo_path, caption="Uploaded Photo", width=300)
            uploaded_file = st.file_uploader("Upload Photo", type=["jpg", "png"], key=f"photo_{tid}")
            if uploaded_file:
                photo_path = f"photos/task_{tid}_{uploaded_file.name}"
                with open(photo_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                update_task_photo(tid, photo_path)
                st.success("Photo uploaded!")
                st.rerun()
            
            if is_management:
                new_due = st.date_input("Update Due Date", value=datetime.strptime(due, "%Y-%m-%d") if due else datetime.now(), key=f"due_{tid}")
                if str(new_due) != due:
                    update_task_due_date(tid, new_due.strftime("%Y-%m-%d"))
                    st.rerun()

# --- My Tasks Tab ---
def my_tasks():
    st.header(f"My Tasks ({st.session_state.user})")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT t.id, p.name, t.area, t.main_task, t.sub_task, t.due_date, t.completed, t.completed_date, t.comments, t.photo_path
        FROM tasks t JOIN projects p ON t.project_id = p.id
        JOIN employees e ON t.assigned_to = e.id
        WHERE e.id = ? AND t.completed = 0
        ORDER BY t.due_date
    """, (st.session_state.user_id,))
    tasks = cur.fetchall()
    
    for task in tasks:
        tid, proj, area, main, sub, due, comp, cdate, comments, photo_path = task
        with st.expander(f"Project: {proj} | {area} – {main} / {sub} | Due: {due}"):
            completed = st.checkbox("Mark Complete", value=bool(comp), key=f"my_comp_{tid}")
            if completed != bool(comp):
                toggle_task_completed(tid, completed)
                st.rerun()
            
            new_comments = st.text_area("Comments", value=comments or "", key=f"my_comments_{tid}")
            if new_comments != (comments or ""):
                update_task_comments(tid, new_comments)
                st.rerun()
            
            if photo_path:
                st.image(photo_path, caption="Uploaded Photo", width=300)
            uploaded_file = st.file_uploader("Upload Photo", type=["jpg", "png"], key=f"my_photo_{tid}")
            if uploaded_file:
                photo_path = f"photos/task_{tid}_{uploaded_file.name}"
                with open(photo_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                update_task_photo(tid, photo_path)
                st.success("Photo uploaded!")
                st.rerun()

# --- Task Schedule Tab ---
def task_schedule(is_management):
    st.header("Task Schedule")
    rows = get_task_schedule(st.session_state.user_id, is_management)
    if rows:
        df = pd.DataFrame(rows, columns=["ID", "Due Date", "Employee", "Company", "Project", "Area", "Equipment", "Main Task", "Sub Task"])
        st.dataframe(df.style.apply(lambda x: ["background: yellow" if x["Due Date"] < datetime.now().strftime("%Y-%m-%d") else "" for i in x], axis=1))

# --- Run the App ---
if not st.session_state.user:
    login_page()
else:
    main_app()