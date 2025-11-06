# ===============================
# Vocabulary Agent – Full Working Code
# ===============================

import streamlit as st
import os
import re
import json
import requests
import pandas as pd
from datetime import datetime
import markdown2          # pip install markdown2

# --- Shared Header ---
from shared_header import (
    render_header,
    save_feedback_to_admin_session,
    get_shared_data,
    render_unified_business_inputs,
)

# ===============================
# Page Config
# ===============================
st.set_page_config(
    page_title="Vocabulary Agent",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Render Header ---
render_header(
    agent_name="Vocabulary Agent",
    agent_subtitle="Extracts and displays business vocabulary from your problem statement",
    enable_admin_access=True,
    header_height=85
)

# ===============================
# Session State Initialization
# ===============================
for key in [
    "vocab_output", "show_vocabulary", "vocab_feedback_submitted",
    "feedback_option", "analysis_complete", "validation_attempted"
]:
    if key not in st.session_state:
        st.session_state[key] = "" if "output" in key else False

# ===============================
# API Configuration
# ===============================
TENANT_ID = "talos"
HEADERS_BASE = {"Content-Type": "application/json"}
VOCAB_API_URL = (
    "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api"
    "?society_id=1757657318406&agency_id=1758548233201&level=1"
)

API_CONFIGS = [
    {
        "name": "vocabulary",
        "url": VOCAB_API_URL,
        "prompt": lambda problem, _: f"{problem}\n\nExtract the vocabulary from this problem statement."
    }
]

# Feedback CSV
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
FEEDBACK_FILE = os.path.join(BASE_DIR, "feedback.csv")
if not os.path.exists(FEEDBACK_FILE):
    pd.DataFrame(columns=[
        "Timestamp","Employee_id","Feedback","FeedbackType",
        "OffDefinitions","Suggestions","Account","Industry","ProblemStatement"
    ]).to_csv(FEEDBACK_FILE, index=False)

# ------------------------------
# Auth token – ONLY environment variable
# ------------------------------
if "auth_token" not in st.session_state:
    st.session_state.auth_token = os.environ.get("AUTH_TOKEN", "")

# ===============================
# Utility Functions
# ===============================
def json_to_text(data):
    if not data:
        return ""
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        for key in ("result","output","content","text","answer","response"):
            if key in data and data[key]:
                return json_to_text(data[key])
        if "data" in data:
            return json_to_text(data["data"])
        for v in data.values():
            if isinstance(v, str) and len(v) > 10:
                return v
        return "\n".join(f"{k}: {json_to_text(v)}" for k, v in data.items() if v)
    if isinstance(data, list):
        return "\n".join(json_to_text(x) for x in data if x)
    return str(data)

def call_api(agent_name, problem, outputs):
    cfg = next((c for c in API_CONFIGS if c["name"] == agent_name), None)
    if not cfg:
        st.error("Invalid API configuration.")
        return None
    payload = {"agency_goal": cfg["prompt"](problem, outputs)}
    headers = HEADERS_BASE.copy()
    headers.update({"Tenant-ID": TENANT_ID, "X-Tenant-ID": TENANT_ID})
    if st.session_state.auth_token:
        headers["Authorization"] = f"Bearer {st.session_state.auth_token}"
    try:
        r = requests.post(cfg["url"], headers=headers, json=payload, timeout=60)
        return json_to_text(r.json()) if r.status_code == 200 else None
    except Exception as e:
        st.error(f"API call failed: {e}")
        return None

def markdown_to_html(md_text: str) -> str:
    if not md_text:
        return "<p>No content</p>"
    md_text = re.sub(r'^\s*s\s+', '', md_text.strip())
    md_text = re.sub(r'\n\s*s\s+', '\n', md_text)
    html = markdown2.markdown(
        md_text,
        extras=["fenced-code-blocks","tables","break-on-newline","cuddled-lists",
                "header-ids","strike","task_list"]
    )
    html = re.sub(r"<p>\s*([^<\n]+?)\s*:</p>", lambda m: f"<p><strong>{m.group(1)}</strong>:</p>", html, flags=re.IGNORECASE)
    html = re.sub(r"<p>", r'<p style="margin:6px 0; line-height:1.45; font-size:0.98rem;">', html)
    return html

# ===============================
# FIXED submit_feedback – ONE clean DataFrame
# ===============================
def submit_feedback(feedback_type, employee_id="", off_definitions="", suggestions="", additional_feedback=""):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    acc = st.session_state.get("current_account", "")
    ind = st.session_state.get("current_industry", "")
    prob = st.session_state.get("current_problem", "")

    # 9 columns in exact order
    columns = [
        "Timestamp","Employee_id","Feedback","FeedbackType",
        "OffDefinitions","Suggestions","Account","Industry","ProblemStatement"
    ]
    row = [
        ts, employee_id, additional_feedback, feedback_type,
        off_definitions, suggestions, acc, ind, prob
    ]

    entry = pd.DataFrame([row], columns=columns)

    # Save to admin session (no timestamp)
    admin_data = {
        "Employee_id": employee_id,
        "Feedback": additional_feedback,
        "FeedbackType": feedback_type,
        "OffDefinitions": off_definitions,
        "Suggestions": suggestions,
        "Account": acc,
        "Industry": ind,
        "ProblemStatement": prob
    }
    save_feedback_to_admin_session(admin_data, "Vocabulary Agent")

    # Append to CSV
    try:
        if os.path.exists(FEEDBACK_FILE):
            df = pd.read_csv(FEEDBACK_FILE)
            # Ensure existing file has all columns
            for c in columns:
                if c not in df.columns:
                    df[c] = ""
            df = df[columns]  # enforce order
            df = pd.concat([df, entry], ignore_index=True)
        else:
            df = entry
        df.to_csv(FEEDBACK_FILE, index=False)
    except Exception:
        if "feedback_data" not in st.session_state:
            st.session_state.feedback_data = pd.DataFrame(columns=columns)
        st.session_state.feedback_data = pd.concat([st.session_state.feedback_data, entry], ignore_index=True)

    st.session_state.vocab_feedback_submitted = True
    return True

# ===============================
# Main Content
# ===============================
shared = get_shared_data()
account = shared.get("account") or ""
industry = shared.get("industry") or ""
problem = shared.get("problem") or ""

st.session_state.current_account = account
st.session_state.current_industry = industry
st.session_state.current_problem = problem

def _norm(val, fallback):
    return val if val and val not in ("Select Account","Select Industry","Select Problem") else fallback

display_account = _norm(account, "Unknown Company")
display_industry = _norm(industry, "Unknown Industry")

account, industry, problem = render_unified_business_inputs(
    page_key_prefix="vocab",
    show_titles=True,
    title_account_industry="Account & Industry",
    title_problem="Business Problem Description",
    save_button_label="Save Problem Details",
)

st.markdown("---")

# ===============================
# Vocabulary Extraction
# ===============================
has_account = account and account != "Select Account"
has_industry = industry and industry != "Select Industry"
has_problem = bool(problem.strip())

extract_btn = st.button(
    "Extract Vocabulary", type="primary", use_container_width=True,
    disabled=not (has_account and has_industry and has_problem)
)

if extract_btn:
    st.session_state.validation_attempted = True
    if not has_account: st.error("Select an account."); st.stop()
    if not has_industry: st.error("Select an industry."); st.stop()
    if not has_problem: st.error("Enter a problem."); st.stop()

    ctx = f"Business Problem:\n{problem.strip()}\n\nContext:\nAccount: {account}\nIndustry: {industry}"
    with st.spinner("Extracting vocabulary (60-90s)"):
        prog = st.progress(0)
        result = call_api("vocabulary", ctx, {})
        prog.progress(0.5)
        if result and "error" not in result.lower():
            st.session_state.vocab_output = result
            st.session_state.show_vocabulary = True
            st.session_state.analysis_complete = True
            prog.progress(1.0)
            st.success("Extraction complete!")
        else:
            st.session_state.vocab_output = "No data"
            st.session_state.show_vocabulary = True
            st.error("API returned no data")

# ===============================
# Display Vocabulary + Feedback
# ===============================
if st.session_state.get("show_vocabulary") and st.session_state.get("vocab_output"):
    st.markdown("---")

    # ---- Header ----
    st.markdown(
        f"""
        <div style="margin:20px 0;">
            <div class="section-title-box" style="padding:1rem 1.5rem; background:#8b1e1e; border-radius:12px;">
                <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; color:white;">
                    <h3 style="margin:0; font-weight:800; font-size:1.4rem;">Vocabulary</h3>
                    <p style="font-size:0.95rem; margin:8px 0 0; max-width:800px; text-align:center;">
                        AI-generated from <strong>{display_account}</strong> ({display_industry}).<br>
                        Something off? Use the feedback section below.
                    </p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---- Markdown to HTML ----
    raw = st.session_state.vocab_output
    try:
        payload = json.loads(raw) if isinstance(raw, str) else raw
        md_src = json_to_text(payload)
    except Exception:
        md_src = raw

    html_body = markdown_to_html(md_src)

    if display_account != "Unknown Company":
        html_body = re.sub(r'\bthe company\b', display_account, html_body, flags=re.IGNORECASE)
    if display_industry != "Unknown Industry":
        html_body = re.sub(r'\bthe industry\b', display_industry, html_body, flags=re.IGNORECASE)

    # ---- Render Vocabulary Box (once) ----
    st.markdown(
        f"""
        <div style="background:var(--bg-card); border:2px solid #8b1e1e; border-radius:16px; padding:1.6rem; margin-bottom:1.6rem; box-shadow:0 3px 10px rgba(139,30,30,0.15);">
            <h4 style="color:#8b1e1e; font-weight:700; font-size:1.15rem; margin:0 0 1rem; border-bottom:2px solid #8b1e1e; padding-bottom:0.5rem;">
                Key Terminology
            </h4>
            <div style="color:var(--text-primary); line-height:1.3; font-size:1rem;">
                {html_body}

        """,
        unsafe_allow_html=True,
    )

    # ---- Employee ID ----
    def get_employee_id():
        keys = ["employee_id","user_id","userID","EmployeeID","user","username","email"]
        for k in keys:
            if k in st.session_state and st.session_state[k]:
                return st.session_state[k]
        try:
            sh = get_shared_data()
            for k in keys:
                if k in sh and sh[k]:
                    return sh[k]
        except Exception:
            pass
        return "Not Available"
    employee_id = get_employee_id()

    # ---- Feedback Wrapper ----
    def submit_feedback_wrapper(feedback_type, employee_id="", off_definitions="", suggestions="", additional_feedback=""):
        return submit_feedback(
            feedback_type=feedback_type,
            employee_id=employee_id,
            off_definitions=off_definitions,
            suggestions=suggestions,
            additional_feedback=additional_feedback
        )

    # ---- Parse Sections ----
    def parse_sections(txt):
        secs = {}
        cur = None
        for line in txt.split("\n"):
            line = line.strip()
            m = re.match(r"^Section\s+(\d+):\s*(.+)", line, re.I)
            if m:
                cur = f"Section {m.group(1)}: {m.group(2).strip()}"
                secs[cur] = []
                continue
            if cur and line:
                it = re.match(r"^(\d+)\.\s+(.+?)(?::|$)", line)
                if it:
                    term = re.sub(r":\s*$", "", it.group(2).strip())
                    secs[cur].append(term)
        return secs
    sections_data = parse_sections(st.session_state.vocab_output)

    # ---- Feedback UI ----
    if not st.session_state.get('vocab_feedback_submitted', False):
        fb_choice = st.radio(
            "Select your feedback type:",
            options=[
                "I have read it, found it useful, thanks.",
                "I have read it, found some definitions to be off.",
                "The widget seems interesting, but I have some suggestions on the features.",
            ],
            index=None,
            key="vocab_feedback_radio",
        )

        if fb_choice == "I have read it, found it useful, thanks.":
            with st.form("vocab_feedback_form_positive", clear_on_submit=True):
                st.info("Thank you for your positive feedback!")
                st.markdown(f'**Employee ID:** {employee_id}')
                if st.form_submit_button("Submit Positive Feedback"):
                    submit_feedback_wrapper(fb_choice, employee_id=employee_id)
                    st.rerun()

        elif fb_choice == "I have read it, found some definitions to be off.":
            with st.form("vocab_feedback_form_defs", clear_on_submit=True):
                st.markdown("**Please select which sections and terms have definitions that seem off:**")
                st.markdown(f'**Employee ID:** {employee_id}')
                section_display_names = [
                    "Extract and Define Business Vocabulary Terms",
                    "Identify KPIs and Metrics",
                    "Identify Relevant Business Processes",
                    "Present a Cohesive Narrative"
                ]
                # Single dropdown for section selection
                selected_section = st.selectbox(
                    "Select the section:",
                    options=section_display_names,
                    key="vocab_section_selectbox"
                )
                # Map display names to section keys in sections_data
                section_key_map = {
                    "Extract and Define Business Vocabulary Terms": "Section 1: Extract and Define Business Vocabulary Terms",
                    "Identify KPIs and Metrics": "Section 2: Identify KPIs and Metrics",
                    "Identify Relevant Business Processes": "Section 3: Identify Relevant Business Processes",
                    "Present a Cohesive Narrative": "Section 4: Present a Cohesive Narrative"
                }
                sel = []
                addl = st.text_input("Additional comments (optional):", key="vocab_definitions_additional")
                if st.form_submit_button("Submit Feedback"):
                    if not sel and not addl.strip():
                        st.warning("Please select at least one term or provide comments.")
                    else:
                        submit_feedback_wrapper(
                            fb_choice,
                            employee_id=employee_id,
                            off_definitions=selected_section,
                            additional_feedback=addl
                        )
                        st.rerun()

        elif fb_choice == "The widget seems interesting, but I have some suggestions on the features.":
            with st.form("vocab_feedback_form_suggestions", clear_on_submit=True):
                st.markdown("**Please share your suggestions for improvement:**")
                st.markdown(f'**Employee ID:** {employee_id}')
                sugg = st.text_input("Your suggestions:", key="vocab_suggestions_input")
                if st.form_submit_button("Submit Feedback"):
                    if sugg.strip():
                        submit_feedback_wrapper(fb_choice, employee_id=employee_id, suggestions=sugg)
                        st.rerun()
                    else:
                        st.warning("Please provide your suggestions.")
    else:
        st.markdown('<div class="feedback-success">Thank you! Your feedback has been recorded.</div>', unsafe_allow_html=True)
        if st.button("Submit Another Feedback", key="vocab_reopen_feedback_btn", use_container_width=True):
            st.session_state.vocab_feedback_submitted = False
            st.rerun()

# Enhanced CSS for proper dark mode dropdown visibility
st.markdown("""
<style>
    /* DARK MODE DROPDOWN FIXES - COMPREHENSIVE */
    /* Fix all dropdown backgrounds to match text input */
    div[data-baseweb="select"] > div {
        background-color: white !important;
        color: #1f2937 !important;
        border: 2px solid rgba(255,0,0,0.3) !important;
    }

    div[data-baseweb="select"] > div:hover {
        ackground-color: white !important;
        color: #1f2937 !important;
        border-color: rgba(255,0,0,0.5) !important;
    }
    
    /* Fix dropdown text color */
    div[data-baseweb="select"] span {
        color: white !important;
    }
    
    /* Fix dropdown placeholder */
    div[data-baseweb="select"] input::placeholder {
        color: #cccccc !important;
    }
    
    /* Fix dropdown arrow */
    div[data-baseweb="select"] svg {
        fill: white !important;
    }
    
    /* FIX DROPDOWN POPOVER BACKGROUND - Make it dark like text inputs */
    [data-baseweb="popover"] {
        background-color: white !important;
        border: 2px solid rgba(255,0,0,0.5) !important;
    }
    
    /* FIX DROPDOWN OPTIONS LIST BACKGROUND - Make it dark */
    [data-baseweb="popover"] > div {
        background-color: #1f2937 !important;
        color: white !important;
    }
    
    /* Fix dropdown options */
    [role="listbox"] [role="option"] {
        background-color: #1f2937 !important;
        color: white !important;
    }
    
    [role="listbox"] [role="option"]:hover {
        background-color: #374151 !important;
        color: white !important;
    }
    
    /* Fix selected options */
    [aria-selected="true"] {
        background-color: #8b1e1e !important;
        color: white !important;
    }
    
    /* Fix multiselect tags */
    [data-baseweb="tag"] {
        background-color: #8b1e1e !important;
        color: white !important;
        border: 1px solid white !important;
    }
    
    /* Style text inputs to match - Additional comments box */
    .stTextInput input {
        background-color: #1f2937 !important;
        color: white !important;
        border: 2px solid rgba(255,255,255,0.3) !important;
    }
    
    .stTextInput input:focus {
        border-color: #8b1e1e !important;
    }
    
    /* Reduce dropdown width */
    .stMultiSelect {
        min-width: 250px !important;
    }
    
    /* SUBMIT BUTTON STYLING - VIBRANT MU SIGMA RED */
    .stButton button {
        background-color: #D32F2F !important;
        color: white !important;
        border: none !important;
        padding: 0.5rem 1.5rem !important;
        border-radius: 6px !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
    }
    
    .stButton button:hover {
        background-color: #B71C1C !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(211, 47, 47, 0.4) !important;
    }
    
    .stButton button:focus {
        background-color: #D32F2F !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 0 0 3px rgba(211, 47, 47, 0.3) !important;
    }
    
    /* Form submit buttons */
    [data-testid="baseButton-secondaryFormSubmit"] {
        background-color: #D32F2F !important;
        color: white !important;
        border: none !important;
        font-weight: 700 !important;
    }
    
    [data-testid="baseButton-secondaryFormSubmit"]:hover {
        background-color: #B71C1C !important;
        color: white !important;
        border: none !important;
    }
    
    /* Ensure all popover content is dark */
    [data-baseweb="popover"] * {
    }
    
    /* Specific fix for the options list container */
    [data-baseweb="popover"] [role="listbox"] {
        background-color: #1f2937 !important;
    }
    
    /* Fix for the individual option items */
    [data-baseweb="popover"] [role="option"] {
        background-color: white !important;
        color: black !important;
    }
    
    [data-baseweb="popover"] [role="option"]:hover {
        background-color: #374151 !important;
        color: white !important;
    }
    
</style>
""", unsafe_allow_html=True)
# ===============================
# Download Section - Only show if feedback submitted FOR THIS AGENT
# ===============================

if st.session_state.get('vocab_feedback_submitted', False):  # CHANGED
    st.markdown("---")
    st.markdown(
        """
        <div style="margin: 10px 0;">
            <div class="section-title-box" style="padding: 0.5rem 1rem;">
                <div style="display:flex; flex-direction:column; align-items:center; justify-content:center;">
                    <h3 style="margin:0; color:white; font-weight:700; font-size:1.2rem; line-height:1.2;">
                        📥 Download Vocabulary
                    </h3>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    vocab_text = st.session_state.get("vocab_output", "")
    if vocab_text and not vocab_text.startswith("API Error") and not vocab_text.startswith("Error:"):
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"vocabulary_{display_account.replace(' ', '_')}_{ts}.txt"
        download_content = f"""Vocabulary Export
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Company: {display_account}
Industry: {display_industry}

{vocab_text}

---
Generated by Vocabulary Analysis Tool
"""
        st.download_button(
            "⬇️ Download Vocabulary as Text File",
            data=download_content,
            file_name=filename,
            mime="text/plain",
            use_container_width=True
        )
    else:
        st.info(
            "No vocabulary available for download. Please complete the analysis first.")
# =========================================
# ⬅️ BACK BUTTON
# =========================================
st.markdown("---")
if st.button("Back to Main Page", use_container_width=True):
    st.switch_page("Welcome_Agent.py")