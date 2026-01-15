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
    cur.execute("INSERT INTO employees (name, surname, position, role, pin) VALUES (?, ?, ?, ?, ?)", (name, surname, position, role, pin))
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

def get_projects_by_company(company_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id, p.name, p.progress, p.overall_completion, p.archived, p.owner_id, e.name || ' ' || e.surname AS owner_name
        FROM projects p
        LEFT JOIN employees e ON p.owner_id = e.id
        WHERE p.company_id = ?
        ORDER BY p.name
    """, (company_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_active_projects(company_id, user_id, is_management):
    projects = get_projects_by_company(company_id)
    filtered = [p for p in projects if (p[3] == 0 or p[2] < 100) and (is_management or p[5] == user_id)]
    return filtered

def get_archived_projects(company_id, user_id, is_management):
    projects = get_projects_by_company(company_id)
    filtered = [p for p in projects if p[3] == 1 and p[2] == 100 and (is_management or p[5] == user_id)]
    return filtered

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

def toggle_task_completed(task_id, completed):
    conn = get_connection()
    cur = conn.cursor()

    completed_date = None
    if completed:
        completed_date = datetime.now().strftime("%Y-%m-%d")

    cur.execute("""
        UPDATE tasks
        SET completed = ?, completed_date = ?
        WHERE id = ?
    """, (int(completed), completed_date, task_id))

    conn.commit()
    conn.close()

def update_task_comments(task_id, comments):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET comments = ? WHERE id = ?", (comments, task_id))
    conn.commit()
    conn.close()

def update_task_photo(task_id, photo_path):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET photo_path = ? WHERE id = ?", (photo_path, task_id))
    conn.commit()
    conn.close()

def update_task_due_date(task_id, due_date):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET due_date = ? WHERE id = ?", (due_date, task_id))
    conn.commit()
    conn.close()

def update_task_weight(task_id, weight):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET weight = ? WHERE id = ?", (weight, task_id))
    conn.commit()
    conn.close()

def get_tasks_by_status(project_id, status, user_id, is_management):
    conn = get_connection()
    cur = conn.cursor()
    sql = """
        SELECT t.id, t.area, t.equipment, t.main_task, t.sub_task, t.due_date, t.completed, t.completed_date, e.name || ' ' || e.surname AS assigned_to, t.comments, t.photo_path, t.weight
        FROM tasks t
        LEFT JOIN employees e ON t.assigned_to = e.id
        WHERE t.project_id = ? AND t.archived = 0
    """
    params = [project_id]
    today = datetime.now().strftime("%Y-%m-%d")
    if status == 'active':
        sql += " AND t.completed = 0 AND (t.due_date >= ? OR t.due_date IS NULL)"
        params.append(today)
    elif status == 'completed':
        sql += " AND t.completed = 1"
    elif status == 'overdue':
        sql += " AND t.completed = 0 AND t.due_date < ?"
        params.append(today)
    if not is_management:
        sql += " AND t.assigned_to = ?"
        params.append(user_id)
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return rows

# Streamlit App

init_db()

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
if not st.session_state.user:
    login_page()
else:
    if st.session_state.role == 'site':
        site_user_page()
    else:
        management_page()

def login_page():
    st.title("Login - CSES Project Management")
    
    users = [f"{name} {surname}" for eid, name, surname, position, role, pin in get_employees()]
    if not users:
        users = ["admin"]
    user = st.selectbox("Select User", users)
    pin = st.text_input("Enter PIN", type="password")
    
    if st.button("Login"):
        if user and pin:
            eid, role, stored_pin = get_employee_details(user)
            if pin == stored_pin and eid:
                st.session_state.user = user
                st.session_state.user_id = eid
                st.session_state.role = role
                st.rerun()
            else:
                st.error("Invalid PIN")
        else:
            st.error("Select user and enter PIN")

# Site User Page
def site_user_page():
    st.title(f"Welcome, {st.session_state.user} (Site)")
    st.header("Your Assigned Projects and Tasks")
    projects = get_projects_by_company(st.session_state.company_id, st.session_state.user_id, False)
    for p in projects:
        pid, name, progress, overall_completion, archived, owner_id, owner_name = p
        with st.expander(name):
            tasks = get_project_tasks(pid, st.session_state.user_id, False)
            for t in tasks:
                tid, area, equip, main, sub, due, comp, cdate, assigned, comments, photo_path, weight = t
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
    if os.path.exists("CSES Logo.png"):
        st.image("CSES Logo.png", width=200)
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
                accept_assignment(proj['id'])
                st.rerun()

    # Sidebar
    with st.sidebar:
        if st.button("Create new company"):
            st.session_state.create_company_form = True
        st.subheader("Clients and Projects")
        companies = get_companies()
        company_names = [name for id, name, address, contact in companies]
        selected_company = st.selectbox("Select Client", company_names)
        if selected_company:
            st.session_state.company_id = next(id for id, name, _, _ in companies if name == selected_company)
        
        if st.session_state.company_id:
            if st.button("Active Projects"):
                projects = get_active_projects(st.session_state.company_id, st.session_state.user_id, True)
                for p in projects:
                    pid, name, progress, overall_completion, archived, owner_id, owner_name = p
                    st.write(name)
                    if st.checkbox("Overall Completion", value=bool(overall_completion), key=f"complete_{pid}"):
                        mark_overall_completion(pid, 1)
                        st.rerun()
            
            if st.button("Archived Projects"):
                projects = get_archived_projects(st.session_state.company_id, st.session_state.user_id, True)
                for p in projects:
                    pid, name, progress, overall_completion, archived, owner_id, owner_name = p
                    st.write(name)

    # Main area for create company form
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
        task_builder(st.session_state.project_id, st.session_state.user_id, True)

    with tab2:
        active_tasks(st.session_state.project_id, st.session_state.user_id, True)

    with tab3:
        my_tasks(st.session_state.user_id)

    with tab4:
        task_schedule(st.session_state.user_id, True)

    with tab5:
        manage_employees()

    with tab6:
        manage_clients()

    with tab7:
        manage_projects()

    with tab8:
        project_status(st.session_state.project_id, st.session_state.user_id, True)

# Implement task_builder (former scope_builder)
def task_builder(project_id, user_id, is_management):
    st.header("Task Builder")
    # Form for tasks, with weight field for management/Project Owner
    if is_management:
        # Add task form
        area = st.selectbox("Area", DEFAULT_AREAS)
        # ... (full form as before, add weight = st.number_input("Weight", min_value=0.0, value=1.0))
        if st.button("Add Task"):
            # Insert with weight
            pass

    # Display tasks with weight edit for owner

# Similar for other functions, with permissions

# Run the app