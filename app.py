# app.py - Updated Streamlit Web App for CSES Project Management
# Run with: streamlit run app.py

import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3
import os
from functools import lru_cache

# Create photos folder if not exists
os.makedirs("photos", exist_ok=True)

# Database functions

DB_NAME = "project_manager.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Companies (added address, contact_number)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            address TEXT,
            contact_number TEXT
        )
    """)

    # Company representatives
    cur.execute("""
        CREATE TABLE IF NOT EXISTS company_representatives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            position TEXT
        )
    """)

    # Employees (added surname, position)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            surname TEXT NOT NULL,
            position TEXT,
            role TEXT DEFAULT 'site',  -- management or site
            pin TEXT,
            active INTEGER DEFAULT 1
        )
    """)

    # Projects (changed representative_id to owner_id, added new_assignment)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            quote_number TEXT,
            project_number TEXT,
            owner_id INTEGER NOT NULL,  -- Employee ID of Project Owner
            progress REAL DEFAULT 0,
            overall_completion INTEGER DEFAULT 0,
            archived INTEGER DEFAULT 0,
            new_assignment INTEGER DEFAULT 1
        )
    """)

    # Tasks (added weight)
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
            comments TEXT,
            photo_path TEXT,
            weight REAL DEFAULT 1.0,
            archived INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()

    # Seed management employees if not exist
    add_employee("Jaco", "Kotze", "Manager", "management", "1234")
    add_employee("Craig", "Brooks", "Manager", "management", "5678")

# ---------------- COMPANIES ----------------

def add_company(name, address='', contact_number=''):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO companies (name, address, contact_number) VALUES (?, ?, ?)", (name, address, contact_number))
    conn.commit()
    conn.close()

def get_companies():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, address, contact_number FROM companies ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return rows

def update_company(company_id, name, address, contact_number):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE companies SET name = ?, address = ?, contact_number = ? WHERE id = ?", (name, address, contact_number, company_id))
    conn.commit()
    conn.close()

# ---------------- REPRESENTATIVES ----------------

def get_company_representatives(company_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, position FROM company_representatives WHERE company_id = ?", (company_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def add_company_representative(company_id, name, position):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO company_representatives (company_id, name, position) VALUES (?, ?, ?)", (company_id, name, position))
    conn.commit()
    conn.close()

# ---------------- EMPLOYEES ----------------

def add_employee(name, surname, position, role='site', pin=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO employees (name, surname, position, role, pin) VALUES (?, ?, ?, ?, ?)", (name, surname, position, role, pin))
    conn.commit()
    conn.close()

def get_employees():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, surname, position, role, pin FROM employees WHERE active=1 ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return rows

def update_employee(employee_id, name, surname, position, role, pin):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE employees SET name = ?, surname = ?, position = ?, role = ?, pin = ? WHERE id = ?", (name, surname, position, role, pin, employee_id))
    conn.commit()
    conn.close()

# ---------------- PROJECTS ----------------

def add_project(company_id, name, description, quote_number, project_number, owner_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO projects (
            company_id, name, description, quote_number,
            project_number, owner_id, new_assignment
        )
        VALUES (?, ?, ?, ?, ?, ?, 1)
    """, (company_id, name, description, quote_number, project_number, owner_id))
    conn.commit()
    conn.close()

def get_projects_by_company(company_id, user_id, is_management):
    conn = get_connection()
    cur = conn.cursor()
    sql = """
        SELECT p.id, p.name, p.progress, p.overall_completion, p.archived, e.name || ' ' || e.surname AS owner_name
        FROM projects p
        LEFT JOIN employees e ON p.owner_id = e.id
        WHERE p.company_id = ?
    """
    params = [company_id]
    if not is_management:
        sql += " AND p.owner_id = ?"
        params.append(user_id)
    sql += " ORDER BY p.name"
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return rows

def get_active_projects(company_id, user_id, is_management):
    projects = get_projects_by_company(company_id, user_id, is_management)
    return [p for p in projects if p[2] < 100 or p[3] == 0]

def get_archived_projects(company_id, user_id, is_management):
    projects = get_projects_by_company(company_id, user_id, is_management)
    return [p for p in projects if p[3] == 1]

def mark_overall_completion(project_id, completed):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE projects SET overall_completion = ?, archived = ? WHERE id = ?", (completed, completed, project_id))
    conn.commit()
    conn.close()

def accept_assignment(project_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE projects SET new_assignment = 0 WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()

def get_new_assignments(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM projects WHERE owner_id = ? AND new_assignment = 1", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [{'id': r[0], 'name': r[1]} for r in rows]

def recalc_project_progress(project_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT SUM(weight * completed) / SUM(weight) * 100
        FROM tasks
        WHERE project_id = ? AND archived = 0
    """, (project_id,))
    progress = cur.fetchone()[0] or 0
    cur.execute("UPDATE projects SET progress = ? WHERE id = ?", (progress, project_id))
    conn.commit()
    conn.close()

# ---------------- TASKS ----------------

def insert_task(project_id, area, equipment, kw, main_task, sub_task, assigned_to, due_date, weight=1.0, comments='', photo_path=''):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO tasks (
            project_id, area, equipment, kw,
            main_task, sub_task, assigned_to, due_date, weight, comments, photo_path
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        project_id, area, equipment, kw,
        main_task, sub_task, assigned_to, due_date, weight, comments, photo_path
    ))
    conn.commit()
    conn.close()

def get_project_tasks(project_id, user_id, is_management):
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
            e.name || ' ' || e.surname AS assigned_to,
            t.comments,
            t.photo_path,
            t.weight
        FROM tasks t
        LEFT JOIN employees e ON t.assigned_to = e.id
        WHERE t.project_id = ? AND t.archived = 0
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

# Additional functions for update_task_weight, etc.

def update_task_weight(task_id, weight):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET weight = ? WHERE id = ?", (weight, task_id))
    conn.commit()
    conn.close()

# Other update functions as before

# Get tasks by status (for Project Status tab)
def get_tasks_by_status(project_id, status, user_id, is_management):
    conn = get_connection()
    cur = conn.cursor()
    sql = "SELECT * FROM tasks WHERE project_id = ? AND archived = 0"
    params = [project_id]
    if status == 'active':
        sql += " AND completed = 0 AND (due_date >= ? OR due_date IS NULL)"
        params.append(datetime.now().strftime("%Y-%m-%d"))
    elif status = 'completed':
        sql += " AND completed = 1"
    elif status = 'overdue':
        sql += " AND completed = 0 AND due_date < ?"
        params.append(datetime.now().strftime("%Y-%m-%d"))
    if not is_management:
        sql += " AND assigned_to = ?"
        params.append(user_id)
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return rows

# Streamlit App

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
if "create_company_form" not in st.session_state:
    st.session_state.create_company_form = False

# Login page
def login_page():
    st.title("Login - CSES Project Management")
    
    users = [f"{name} {surname}" for _, name, surname, _, _, _ in get_employees()]
    if not users:
        users = ["admin"]
    user = st.selectbox("Select User", users)
    pin = st.text_input("Enter PIN", type="password")
    
    if st.button("Login"):
        if user and pin:
            full_name = user
            eid, role, stored_pin = get_employee_details(full_name)
            if pin == stored_pin:
                st.session_state.user = full_name
                st.session_state.user_id = eid
                st.session_state.role = role
                st.rerun()
            else:
                st.error("Invalid PIN")
        else:
            st.error("Select user and enter PIN")

# Get employee details by full name
def get_employee_details(full_name):
    name, surname = full_name.split(' ', 1) if ' ' in full_name else (full_name, '')
    employees = get_employees()
    for eid, ename, esurname, eposition, erole, epin in employees:
        if ename == name and esurname == surname:
            return eid, erole, epin
    return None, None, None

# Site User Page
def site_user_page():
    st.title(f"Welcome, {st.session_state.user} (Site)")
    st.header("Your Assigned Projects and Tasks")
    projects = get_projects_by_company(st.session_state.company_id, st.session_state.user_id, False)
    for proj in projects:
        st.subheader(proj[1])
        tasks = get_project_tasks(proj[0], st.session_state.user_id, False)
        for task in tasks:
            tid, area, equip, main, sub, due, comp, cdate, assigned, comments, photo_path, weight = task
            with st.expander(f"{area} – {main} / {sub} | Due: {due}"):
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

# Management Page
def management_page():
    st.image("CSES Logo.png", width=200) if os.path.exists("CSES Logo.png") else st.write("")
    st.title(f"Welcome, {st.session_state.user} (Management)")
    
    # Pop-up for new assignments
    new_projects = get_new_assignments(st.session_state.user_id)
    if new_projects:
        for proj in new_projects:
            st.info(f"You have been assigned a new Project: {proj['name']}")
            if st.button("Take me there", key=f"take_{proj['id']}"):
                st.session_state.project_id = proj['id']
                st.rerun()
            if st.button("Accept", key=f"accept_{proj['id']}"):
                accept_assignment(proj['id']}
                st.rerun()
    
    # Sidebar
    with st.sidebar:
        if st.button("Create new company"):
            st.session_state.create_company_form = True
        
        st.subheader("Clients and Projects")
        companies = get_companies()
        company_names = [name for _, name, _, _ in companies]
        selected_company = st.selectbox("Select Client", company_names)
        if selected_company:
            st.session_state.company_id = next(id for id, name, _, _ in companies if name == selected_company)
        
        if st.session_state.company_id:
            if st.button("Active Projects"):
                projects = get_active_projects(st.session_state.company_id, st.session_state.user_id, True)
                for p in projects:
                    st.write(p[1])
                    if st.checkbox("Overall Completion", value=bool(p[3]), key=f"complete_{p[0]}"):
                        mark_overall_completion(p[0], 1)
                        st.rerun()
            
            if st.button("Archived Projects"):
                projects = get_archived_projects(st.session_state.company_id, st.session_state.user_id, True)
                for p in projects:
                    st.write(p[1])
    
    # Main area for forms
    if st.session_state.create_company_form:
        st.header("Create New Company")
        name = st.text_input("Name")
        address = st.text_area("Address")
        contact_number = st.text_input("Contact Number")
        if st.button("Save"):
            add_company(name, address, contact_number)
            st.success("Company added!")
            st.session_state.create_company_form = False
            st.rerun()

    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(["Task Builder", "Active Tasks", "My Tasks", "Schedule", "Manage Employees", "Manage Clients", "Manage Projects", "Project Status"])

    with tab1:
        task_builder()

    with tab2:
        active_tasks()

    with tab3:
        my_tasks()

    with tab4:
        task_schedule()

    with tab5:
        manage_employees()

    with tab6:
        manage_clients()

    with tab7:
        manage_projects()

    with tab8:
        project_status()

# Implement each function as per amendments (task_builder as renamed scope_builder, manage_employees with add/edit form, etc.)

def manage_employees():
    st.header("Manage Employees")
    employees = get_employees()
    for emp in employees:
        with st.expander(f"{emp[1]} {emp[2]}"):
            new_name = st.text_input("Name", emp[1], key=f"name_{emp[0]}")
            new_surname = st.text_input("Surname", emp[2], key=f"surname_{emp[0]}")
            new_position = st.text_input("Position", emp[3], key=f"position_{emp[0]}")
            new_role = st.selectbox("Role", ["management", "site"], index=0 if emp[4] == 'management' else 1, key=f"role_{emp[0]}")
            new_pin = st.text_input("PIN", emp[5], type="password", key=f"pin_{emp[0]}")
            if st.button("Update", key=f"update_{emp[0]}"):
                update_employee(emp[0], new_name, new_surname, new_position, new_role, new_pin)
                st.success("Updated!")
                st.rerun()

    st.subheader("Add New Employee")
    name = st.text_input("Name")
    surname = st.text_input("Surname")
    position = st.text_input("Position")
    role = st.selectbox("Role", ["management", "site"])
    pin = st.text_input("PIN", type="password")
    if st.button("Add Employee"):
        add_employee(name, surname, position, role, pin)
        st.success("Added!")
        st.rerun()

# Similar for manage_clients, manage_projects, project_status, etc.

def project_status():
    st.header("Project Status")
    status = st.selectbox("Select Status", ["Active", "Completed", "Overdue"])
    tasks = get_tasks_by_status(st.session_state.project_id, status, st.session_state.user_id, st.session_state.role == 'management')
    df = pd.DataFrame(tasks, columns=["ID", "Area", "Equipment", "Main Task", "Sub Task", "Due Date", "Completed", "Completed Date", "Assigned To", "Comments", "Photo", "Weight"])
    st.dataframe(df)

    st.subheader("Calendar")
    selected_date = st.date_input("Select Date")
    # Filter tasks by selected date (add logic)

# Run the app
if not st.session_state.user:
    login_page()
else:
    if st.session_state.role == 'site':
        site_user_page()
    else:
        management_page()