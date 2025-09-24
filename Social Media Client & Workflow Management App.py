import streamlit as st
import sqlite3
import hashlib
from datetime import datetime
import os
from fpdf import FPDF

# ===== Config =====
DB_FILE = "database.db"
MEDIA_FOLDER = "media"
REPORT_FOLDER = "reports"

os.makedirs(MEDIA_FOLDER, exist_ok=True)
os.makedirs(REPORT_FOLDER, exist_ok=True)

conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()

# ===== Database Tables =====
c.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                email TEXT,
                password_hash TEXT,
                role TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY,
                name TEXT,
                email TEXT,
                social_accounts TEXT,
                notes TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY,
                client_id INTEGER,
                filename TEXT,
                caption TEXT,
                hashtags TEXT,
                scheduled_time TEXT,
                status TEXT,
                feedback TEXT,
                FOREIGN KEY(client_id) REFERENCES clients(id))''')

conn.commit()

# ===== Create default admin user =====
def create_admin():
    username = "admin"
    password = "admin"
    email = "admin@email.com"
    role = "admin"
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    existing = c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    if not existing:
        c.execute("INSERT INTO users (username,email,password_hash,role) VALUES (?,?,?,?)",
                  (username,email,pw_hash,role))
        conn.commit()

create_admin()

# ===== Utils =====
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_login(username, password):
    pw_hash = hash_password(password)
    user = c.execute("SELECT * FROM users WHERE username=? AND password_hash=?", (username, pw_hash)).fetchone()
    return user

def generate_pdf_report(client_id, client_name):
    posts = c.execute("SELECT filename, caption, hashtags, scheduled_time, status, feedback FROM posts WHERE client_id=?", (client_id,)).fetchall()
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, f"Client Report - {client_name}", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(200, 10, f"Date: {datetime.today().strftime('%Y-%m-%d')}", ln=True)
    pdf.ln(10)
    for post in posts:
        pdf.multi_cell(0, 10, f"Caption: {post[1]}\nHashtags: {post[2]}\nScheduled: {post[3]}\nStatus: {post[4]}\nFeedback: {post[5]}\n{'-'*50}\n")
    filename = os.path.join(REPORT_FOLDER, f"{client_name}_report.pdf")
    pdf.output(filename)
    return filename

# ===== Login =====
if "user" not in st.session_state:
    st.title("Social Media Manager Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = check_login(username, password)
        if user:
            st.session_state["user"] = user
            st.success(f"Logged in as {user[1]}")
        else:
            st.error("Invalid credentials")
    st.stop()

user = st.session_state["user"]
role = user[4]
st.sidebar.write(f"Logged in as: {user[1]} ({role})")

# ===== Admin Menu =====
if role == "admin":
    menu = st.sidebar.selectbox("Menu", ["Dashboard", "Add Client", "Add Post", "Generate Report"])
    
    if menu == "Dashboard":
        st.subheader("All Clients & Posts")
        clients = c.execute("SELECT * FROM clients").fetchall()
        for client in clients:
            st.write(f"**{client[1]}** ({client[2]})")
            posts = c.execute("SELECT * FROM posts WHERE client_id=?", (client[0],)).fetchall()
            for post in posts:
                st.write(f"- {post[3]} | Scheduled: {post[5]} | Status: {post[6]} | Feedback: {post[7]}")

    elif menu == "Add Client":
        st.subheader("Add New Client")
        name = st.text_input("Client Name")
        email = st.text_input("Email")
        social = st.text_input("Social Accounts")
        notes = st.text_area("Notes")
        if st.button("Add Client"):
            c.execute("INSERT INTO clients (name,email,social_accounts,notes) VALUES (?,?,?,?)",
                      (name,email,social,notes))
            conn.commit()
            st.success("Client added successfully!")

    elif menu == "Add Post":
        st.subheader("Schedule New Post")
        clients = c.execute("SELECT id,name FROM clients").fetchall()
        client_dict = {name:id for id,id in clients}
        client_name = st.selectbox("Select Client", [c[1] for c in clients])
        file = st.file_uploader("Upload Media")
        caption = st.text_area("Caption")
        hashtags = st.text_input("Hashtags")
        schedule_time = st.datetime_input("Schedule Time", datetime.now())
        if st.button("Add Post"):
            if file:
                file_path = os.path.join(MEDIA_FOLDER, file.name)
                with open(file_path, "wb") as f:
                    f.write(file.getbuffer())
                c.execute("""INSERT INTO posts (client_id,filename,caption,hashtags,scheduled_time,status)
                             VALUES (?,?,?,?,?,?)""",
                          (client_dict[client_name], file.name, caption, hashtags, schedule_time, "Pending"))
                conn.commit()
                st.success("Post scheduled!")

    elif menu == "Generate Report":
        st.subheader("Generate PDF Report for Client")
        clients = c.execute("SELECT id,name FROM clients").fetchall()
        client_dict = {name:id for id,id in clients}
        client_name = st.selectbox("Select Client", [c[1] for c in clients])
        if st.button("Generate"):
            client_id = client_dict[client_name]
            pdf_file = generate_pdf_report(client_id, client_name)
            st.success(f"Report saved as {pdf_file}")

# ===== Client Menu =====
elif role == "client":
    menu = st.sidebar.selectbox("Menu", ["My Posts Approval"])
    if menu == "My Posts Approval":
        st.subheader("Posts Pending Approval")
        posts = c.execute("""SELECT posts.id, clients.name, filename, caption, hashtags, scheduled_time, status, feedback
                             FROM posts JOIN clients ON posts.client_id=clients.id
                             WHERE clients.email=? AND status='Pending'""", (user[2],)).fetchall()
        for post in posts:
            st.write(f"**{post[1]}** | {post[3]} | Scheduled: {post[5]}")
            feedback = st.text_input(f"Feedback for {post[2]}", key=post[0])
            approve = st.button(f"Approve {post[2]}", key="ap"+str(post[0]))
            reject = st.button(f"Reject {post[2]}", key="rej"+str(post[0]))
            if approve:
                c.execute("UPDATE posts SET status='Approved', feedback=? WHERE id=?", (feedback, post[0]))
                conn.commit()
                st.success("Post approved!")
            if reject:
                c.execute("UPDATE posts SET status='Rejected', feedback=? WHERE id=?", (feedback, post[0]))
                conn.commit()
                st.warning("Post rejected!")
