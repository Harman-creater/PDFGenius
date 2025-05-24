# UPDATE : adding voice (text to voice) 

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st
from utils import create_qa_pipeline
from utils import get_summarizer
import requests
import sqlite3
import os
import shutil
from ingest import embed_documents

import time

from gtts import gTTS
from io import BytesIO
import base64
import streamlit.components.v1 as components
import uuid

# Page settings
st.set_page_config(page_title="Edu Q&A Bot", page_icon="🎓")

# Session state initialization
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = None
if "chat_log" not in st.session_state:
    st.session_state.chat_log = []
if "qa_chain" not in st.session_state:
    st.session_state.qa_chain = None
if "debug" not in st.session_state:
    st.session_state.debug = False
if "pdf_changed" not in st.session_state:
    st.session_state.pdf_changed = False
if "auth_page" not in st.session_state:
    st.session_state.auth_page = "login"

UPLOAD_DIR = "dataset/"

os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_db_connection():
    return sqlite3.connect('auth.db')


# ------------------- AUTH PAGES -------------------
def show_signup_page():
    st.markdown("## 📝 Sign Up to PDFGenius")
    with st.form("signup_form"):
        username = st.text_input("👤 Username")
        email = st.text_input("📧 Email")
        password = st.text_input("🔒 Password", type="password")
        submitted = st.form_submit_button("Sign Up")

        if submitted:
            if username and email and password:
                response = requests.post("http://127.0.0.1:5000/signup", json={
                    "username": username,
                    "email": email,
                    "password": password
                })
                if response.status_code == 201:
                    st.success("🎉 Registered successfully! Please log in.")
                else:
                    st.error(response.json().get("error", "An error occurred during signup."))
            else:
                st.error("⚠️ All fields are required.")

    if st.button("🔁 Already have an account? Log In"):
        st.session_state.authenticated = False
        st.session_state.auth_page = "login"
        st.rerun()

def show_login_page():
    st.markdown("## 🔐 Log In to PDFGenius")
    with st.form("login_form"):
        username = st.text_input("👤 Username")
        password = st.text_input("🔒 Password", type="password")
        submitted = st.form_submit_button("Log In")

        if submitted:
            if username and password:
                response = requests.post("http://127.0.0.1:5000/login", json={
                    "username": username,
                    "password": password
                })

                if st.session_state.debug:
                    st.write(f"Response Code: {response.status_code}")
                    st.write(f"Response Text: {response.text}")

                if response.status_code == 200:
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.success("✅ Login successful!")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error(response.json().get("error", "Invalid credentials."))
            else:
                st.error("⚠️ All fields are required.")

    if st.button("New here? Create an account"):
        st.session_state.authenticated = False
        st.session_state.auth_page = "signup"
        st.rerun()

    if st.button("Forgot Password"):
        st.session_state.authenticated = False
        st.session_state.auth_page = "forgot"
        st.rerun()

def show_forgot_password_page():
    st.markdown("## 🔑 Forgot Password")
    with st.form("forgot_form"):
        email = st.text_input("📧 Enter your registered email")
        submitted = st.form_submit_button("Send Reset Link")

        if submitted:
            if email:
                response = requests.post("http://127.0.0.1:5000/forgot_password", json={"email": email})
                if response.status_code == 200:
                    st.success("📬 Password reset link sent to your email.")
                else:
                    st.error(response.json().get("error", "Failed to send reset link."))
            else:
                st.error("⚠️ Please enter your email.")
        
    if st.button("Log In"):
        st.session_state.authenticated = False
        st.session_state.auth_page = "login"
        st.rerun()


# ---------------------------- FILE MANAGEMENT ---------------------------- #
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_FILE_COUNT = 3

def get_pdf_list():
    """Retrieve list of uploaded PDF files."""
    return [f for f in os.listdir(UPLOAD_DIR) if f.endswith(".pdf")]

def clean_uploader():
    """Clear uploader by resetting the file_uploader key"""
    st.session_state["uploader"] = None

def manage_documents():
    """Sidebar for managing uploaded PDFs."""
    
    st.sidebar.markdown("### 📂 Manage PDFs")

    uploaded_files = st.sidebar.file_uploader(
        "Upload PDF(s)", 
        accept_multiple_files=True, 
        type=["pdf"],
        key="uploader"
    )
    existing_files = get_pdf_list()
    total_files_after_upload = len(existing_files) + len(uploaded_files)
    if uploaded_files:
        if total_files_after_upload > MAX_FILE_COUNT:
            error = st.sidebar.error(f"Limit exceeded: Max {MAX_FILE_COUNT} PDFs allowed. \n({len(existing_files)} already uploaded)")
            time.sleep(3)
            error.empty()

        else:
            successful_uploads = 0
            
            for uploaded_file in uploaded_files:
                if uploaded_file.size > MAX_FILE_SIZE:
                    warning = st.sidebar.warning(f"❌ {uploaded_file.name} is too large (max 5 MB).")
                    time.sleep(3)
                    warning.empty()
                    continue

                file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                successful_uploads += 1

            if successful_uploads > 0:
                st.session_state.pdf_changed = True
                # clean_uploader()
                success = st.sidebar.success(f"Uploaded {successful_uploads} PDF(s).")
                time.sleep(2)
                success.empty()
                st.rerun()

    st.sidebar.markdown("---") 
    st.sidebar.markdown("### 🗂️ Uploaded Files")

    # Initialize delete confirmation in session state
    if "confirm_delete" not in st.session_state:
        st.session_state.confirm_delete = None

    pdf_list = get_pdf_list()

    for pdf in pdf_list:
        col1, col2 = st.sidebar.columns([0.8, 0.2])
        col1.write(pdf)

        if col2.button("🗑", key=f"delete_{pdf}"):
            st.session_state.confirm_delete = pdf  # Mark for deletion confirmation

    # Handle deletion confirmation
    if st.session_state.confirm_delete:
        with st.sidebar.expander("⚠️ Confirm Deletion", expanded=True):
            st.write(
                f"Are you sure you want to delete **{st.session_state.confirm_delete}**?"
            )
            confirm_col1, confirm_col2 = st.columns(2)

            if confirm_col1.button("✅ Delete", key="confirm_yes"):
                if len(existing_files)>1:
                    #Delete the file
                    os.remove(os.path.join(UPLOAD_DIR, st.session_state.confirm_delete))

                    # Update the state
                    st.session_state.pdf_changed = True
                    st.session_state.confirm_delete = None

                    st.rerun() # Refresh list
                    success = st.sidebar.success(f"Deleted {st.session_state.confirm_delete}")
                    time.sleep(2)
                    success.empty()
                else:
                    warning = st.sidebar.warning("⚠️ Cannot delete. Dataset must contain at least one document.")
                    time.sleep(3)
                    warning.empty()
                    st.rerun()

            if confirm_col2.button("❌ Cancel", key="confirm_no"):
                st.session_state.confirm_delete = None  # Cancel deletion
                st.rerun()

    st.sidebar.markdown("---")

    if st.sidebar.button("⚙️ Process Documents"):
        with st.spinner("Processing documents..."):
            if st.session_state.pdf_changed:
                embed_documents()
                st.session_state.qa_chain = None  # clear QA so it reloads
                st.session_state.pdf_changed = False
                success = st.sidebar.success("✅ Documents processed and vectorstore updated!")
                time.sleep(3)
                success.empty()
            else:
                warning = st.sidebar.warning("ℹ️ No changes detected. Skipped reprocessing.")
                time.sleep(3)
                warning.empty()
            
            st.rerun()  # optional but clean refresh
    
    # st.sidebar.markdown("---")
    # st.sidebar.markdown("### 📝 Summarization Option")
    # st.session_state["summarize_mode"] = st.sidebar.checkbox("Enable Summarize Mode", value=False)

# ------------------- CHATBOT PAGE -------------------
@st.cache_resource
def get_cached_pipeline():
    return create_qa_pipeline()

def load_qa_pipeline():
    if not st.session_state.qa_chain:
        with st.spinner("🤖 Just a sec, we're doing cool stuff."):
            try:
                st.session_state.qa_chain = get_cached_pipeline()

            except Exception as e:
                st.error(f"❌ Failed to load the QA pipeline: {e}")

def generate_audio_base64(text):
    tts = gTTS(text=text, lang='en')
    audio_fp = BytesIO()
    tts.write_to_fp(audio_fp)
    audio_fp.seek(0)
    audio_bytes = audio_fp.read()
    audio_base64 = base64.b64encode(audio_bytes).decode()
    return f"data:audio/mp3;base64,{audio_base64}"

def render_audio_toggle(text, uid):
    audio_data_uri = generate_audio_base64(text)
    components.html(f"""
        <audio id="audio_{uid}" src="{audio_data_uri}"></audio>
        <button onclick="
            var audio = document.getElementById('audio_{uid}');
            if (audio.paused) {{
                audio.play();
                this.textContent = '⏹️';
            }} else {{
                audio.pause();
                audio.currentTime = 0;
                this.textContent = '▶️';
            }}
        ">▶️</button>
    """, height=80)

# WITH SUMMARIZATION OPTION
def show_chat_page():
    load_qa_pipeline()
    st.markdown(f"## 🎓 Edu Q&A Assistant")
    st.caption(f"Welcome, **{st.session_state.username}**! Please enter your question below.")

    user_input = st.chat_input("Type your question here...")

    if user_input:
        try:
            retriever = st.session_state.qa_chain.retriever
            docs = retriever.get_relevant_documents(user_input)

            if docs:
                top_docs = docs[:3]  # Efficient summarization
                context = "\n\n".join(doc.page_content for doc in top_docs)

                # if st.session_state.get("summarize_mode"):
                if True:
                    summarizer = get_summarizer()
                    summary = summarizer(context, max_length=180, min_length=60, do_sample=False)[0]["summary_text"]
                    bot_output = f"**Answer:** {summary}"
                else:
                    response = st.session_state.qa_chain.invoke({"query": user_input})
                    raw_output = response.get("result", "")
                    if raw_output.strip().lower() in ["", "i don't know", "not enough information"]:
                        bot_output = "I couldn't find an answer to your question."
                    else:
                        bot_output = raw_output.strip()
            else:
                bot_output = "⚠️ No relevant sections found to answer or summarize your query."

            # Add to chat history
            st.session_state.chat_log.append({"User": user_input, "Bot": bot_output})

        except Exception as e:
            st.error(f"❌ An error occurred: {e}")

    # Render chat messages
    for exchange in st.session_state.chat_log:
        with st.chat_message("user"):
            st.markdown(exchange["User"])
        with st.chat_message("assistant"):
            st.markdown(exchange["Bot"])
            speak_id = str(uuid.uuid4()).replace("-", "")
            render_audio_toggle(exchange["Bot"], speak_id)


# ------------------- MAIN APP LOGIC -------------------

def show_logout_button():
    with st.sidebar:
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.username = None
            st.session_state.chat_log = []
            st.session_state.qa_chain = None
            st.session_state.pdf_changed = False
            st.success("You have been logged out.")
            time.sleep(2)
            st.session_state.auth_page = "login"
            st.rerun()


if st.session_state.authenticated:
    manage_documents()
    show_logout_button()
    show_chat_page()
else:
    st.markdown("# 🎓 Welcome to PDFGenius")
    st.caption("An academic Q&A assistant to help you learn and explore.")
    
    if st.session_state.auth_page == "login":
        show_login_page()
    elif st.session_state.auth_page == "signup":
        show_signup_page()
    elif st.session_state.auth_page == "forgot":
        show_forgot_password_page()



