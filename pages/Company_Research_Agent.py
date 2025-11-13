import streamlit as st
import os
import re
import json
import io
from datetime import datetime
import pandas as pd
import requests

from shared_header import (
    render_header,
    save_feedback_to_admin_session,
    get_shared_data,
    render_unified_business_inputs,
)

# =========================================
# PAGE CONFIG
# =========================================
st.set_page_config(
    page_title="Company Research Agent",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Hide sidebar
st.markdown("<style>[data-testid='stSidebar'] {display: none;}</style>", unsafe_allow_html=True)

# =========================================
# SESSION INITIALIZATION - AGENT-SPECIFIC
# =========================================
session_defaults = {
    'company_output': "",
    'show_company': False,
    'company_feedback_submitted': False,
    'company_feedback_records': [],
    'feedback_option': None,
    'analysis_complete': False,
    'validation_attempted': False
}

for key, val in session_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# =========================================
# API CONFIGURATION
# =========================================
TENANT_ID = "talos"
HEADERS_BASE = {"Content-Type": "application/json"}

COMPANY_API_URL = (
    "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?"
    "society_id=1757657318406&agency_id=1762327921111&level=1"
)

API_CONFIGS = [
    {
        "name": "company_research",
        "url": COMPANY_API_URL,
        "multiround_convo": 2,
        "description": "Company-level research",
        "prompt": lambda problem, outputs: (
            f"{problem}\n\n"
            "To study and explain the company’s overall goals, vision, and direction with full clarity.\n"
            "To analyze all products, services, and operations in detail to understand how the company functions from end to end.\n"
            "To evaluate the company’s financial performance and market position over the past few years using reliable data and reports.\n"
            "To identify and explain the root causes of the company’s key problems, connecting them to both internal operations and external market factors."
        )
    }
]

# =========================================
# FILE & AUTH CONFIG
# =========================================
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
FEEDBACK_FILE = os.path.join(BASE_DIR, "feedback.csv")

try:
    if not os.path.exists(FEEDBACK_FILE):
        df = pd.DataFrame(columns=[
            "Timestamp", "Employee_id", "Feedback", "FeedbackType",
            "OffDefinitions", "Suggestions", "Account", "Industry",
            "ProblemStatement", "Section"
        ])
        df.to_csv(FEEDBACK_FILE, index=False)
except (PermissionError, OSError):
    if 'feedback_data' not in st.session_state:
        st.session_state.feedback_data = pd.DataFrame(
            columns=["Timestamp", "Employee_id", "Feedback", "FeedbackType",
                     "OffDefinitions", "Suggestions", "Account", "Industry",
                     "ProblemStatement", "Section"])

def _init_auth_token():
    token = os.environ.get("AUTH_TOKEN", "")
    try:
        if not token:
            token = st.secrets.get("AUTH_TOKEN", "")
    except Exception:
        pass
    return token or ""

if 'auth_token' not in st.session_state:
    st.session_state.auth_token = _init_auth_token()

# =========================================
# UTILITY FUNCTIONS
# =========================================

def json_to_text(data):
    if not data:
        return ""
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        for key in ("result", "output", "content", "text", "answer", "response"):
            if key in data and data[key]:
                return json_to_text(data[key])
        if "data" in data:
            return json_to_text(data["data"])
        for value in data.values():
            if isinstance(value, str) and len(value) > 10:
                return value
        return "\n".join(f"{k}: {json_to_text(v)}" for k, v in data.items() if v)
    if isinstance(data, list):
        return "\n".join(json_to_text(x) for x in data if x)
    return str(data)

def sanitize_text(text):
    if not text:
        return ""
    text = re.sub(r'^\s*s\s+', '', text.strip())
    text = re.sub(r'\n\s*s\s+', '\n', text)
    text = re.sub(r'Q\d+\s*Answer\s*Explanation\s*:', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = re.sub(r'#+\s*', '', text)
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'^\s*[-*]\s+', '• ', text, flags=re.MULTILINE)
    text = re.sub(r'<\/?[^>]+>', '', text)
    return text.strip()

def format_company_html(text):
    """Enhanced formatting: bold section headers, bullets, clean paragraphs"""
    if not text:
        return "No company data available"

    t = sanitize_text(text)
    t = re.sub(r'(^|\n)\s*\*\s*', '\n• ', t)
    t = re.sub(r'(?m)^(Section\s+\d+[\s:—–]*)\s*(.+)$', r'<strong>\1 \2</strong>', t, flags=re.IGNORECASE)

    lines = t.splitlines()
    n = len(lines)
    i = 0
    paragraph_html = []

    def collect_paragraph(start_idx):
        block = [lines[start_idx]]
        j = start_idx + 1
        while j < n:
            next_line = lines[j]
            if not next_line.strip():
                break
            if re.match(r'^\s*(?:•|\d+\.|-|Section)', next_line):
                break
            block.append(next_line)
            j += 1
        return block, j

    while i < n:
        ln = lines[i].strip()
        if not ln:
            i += 1
            continue

        # Bold section headers
        if re.match(r'^Section\s+\d+', ln, flags=re.IGNORECASE):
            paragraph_html.append(f"<strong>{ln}</strong>")
            i += 1
            continue

        # Start of bullet or numbered list
        if re.match(r'^\s*(?:•|\d+\.|-)\s+', lines[i]):
            block_lines = []
            while i < n and re.match(r'^\s*(?:•|\d+\.|-)\s+', lines[i]):
                block_lines.append(re.sub(r'^\s*(?:•|\d+\.|-)\s+', '• ', lines[i].strip()))
                i += 1
            paragraph_html.extend(block_lines)
            continue

        # Paragraphs
        block, j = collect_paragraph(i)
        clean_block = [b.strip() for b in block if b.strip()]
        if clean_block:
            paragraph_html.append("<br>".join(clean_block))
        i = j

    # Group into final paragraphs
    final_paragraphs = []
    temp = []
    for line in paragraph_html:
        if line:
            temp.append(line)
        elif temp:
            final_paragraphs.append("<br>".join(temp))
            temp = []
    if temp:
        final_paragraphs.append("<br>".join(temp))

    para_wrapped = [
        f"<p style='margin:1rem o.5rem ; line-height:1.65; font-size:0.98rem;'>{p}</p>" for p in final_paragraphs if p.strip()
    ]
    return "\n".join(para_wrapped)

def collect_paragraph(start_idx):
    block = [lines[start_idx]]
    j = start_idx + 1
    while j < n:
        next_line = lines[j]
        if not next_line.strip():
            break
        if re.match(r'^\s*(?:•|\d+\.|-|Section)', next_line):
            break
        block.append(next_line)
        j += 1
    return block, j

# =========================================
# CENTRALIZED API CALL
# =========================================

def call_api(agent_name, problem, outputs):
    config = next((a for a in API_CONFIGS if a["name"] == agent_name), None)
    if not config:
        st.error("Invalid API configuration.")
        return None

    prompt = config["prompt"](problem, outputs)
    payload = {"agency_goal": prompt}

    headers = HEADERS_BASE.copy()
    headers.update({"Tenant-ID": TENANT_ID, "X-Tenant-ID": TENANT_ID})
    if st.session_state.auth_token:
        headers["Authorization"] = f"Bearer {st.session_state.auth_token}"

    retries = 3
    for attempt in range(retries):
        try:
            response = requests.post(config["url"], headers=headers, json=payload, timeout=(15, 180))
            if response.status_code == 200:
                return sanitize_text(json_to_text(response.json()))
            else:
                st.warning(f"Attempt {attempt+1}: API Error {response.status_code}")
        except requests.exceptions.Timeout:
            st.warning(f"Attempt {attempt+1}: Timeout")
        except Exception as e:
            st.warning(f"Attempt {attempt+1}: {str(e)}")

    st.error("API failed after 3 retries.")
    return None

# =========================================
# FEEDBACK SYSTEM
# =========================================

def parse_sections_from_output(text):
    if not text:
        return ["Full Report"]
    pattern = r'(Section\s+\d+[\s:—–][^\n]+)'
    matches = re.findall(pattern, text, flags=re.IGNORECASE)
    unique = []
    seen = set()
    for m in matches:
        if m.lower() not in seen:
            seen.add(m.lower())
            unique.append(m.strip())
    return unique or ["Full Report"]

def get_employee_id():
    keys = ["employee_id", "user_id", "userID", "EmployeeID", "user", "username", "email"]
    for k in keys:
        if k in st.session_state and st.session_state[k]:
            return st.session_state[k]
    try:
        shared_data = get_shared_data()
        for k in keys:
            if k in shared_data and shared_data[k]:
                return shared_data[k]
    except Exception:
        pass
    return "Not Available"

def submit_feedback(section, feedback_type, user_id, off_definitions="", suggestions="", additional_feedback=""):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    account = st.session_state.get("current_account", "")
    industry = st.session_state.get("current_industry", "")
    problem = st.session_state.get("current_problem", "")

    feedback_data = {
        "Employee_id": user_id,
        "Feedback": additional_feedback,
        "FeedbackType": feedback_type,
        "OffDefinitions": off_definitions,
        "Suggestions": suggestions,
        "Account": account,
        "Industry": industry,
        "ProblemStatement": problem,
        "Section": section,
        "Timestamp": timestamp
    }

    try:
        save_feedback_to_admin_session(feedback_data, "Company Research Agent")
    except Exception:
        pass

    columns = ["Timestamp", "Employee_id", "Feedback", "FeedbackType",
               "OffDefinitions", "Suggestions", "Account", "Industry",
               "ProblemStatement", "Section"]

    row = [timestamp, user_id, additional_feedback, feedback_type,
           off_definitions, suggestions, account, industry, problem, section]

    entry = pd.DataFrame([row], columns=columns)

    try:
        if os.path.exists(FEEDBACK_FILE):
            df = pd.read_csv(FEEDBACK_FILE)
            for c in columns:
                if c not in df.columns:
                    df[c] = ""
            df = df[columns]
            df = pd.concat([df, entry], ignore_index=True)
        else:
            df = entry
        df.to_csv(FEEDBACK_FILE, index=False)
    except Exception:
        if "company_feedback_data" not in st.session_state:
            st.session_state.company_feedback_data = pd.DataFrame(columns=columns)
        st.session_state.company_feedback_data = pd.concat([st.session_state.company_feedback_data, entry], ignore_index=True)

    st.session_state.company_feedback_records.append(feedback_data)
    st.session_state.company_feedback_submitted = True
    return True

# =========================================
# UI RENDERING
# =========================================
render_header(
    agent_name="Company Research Agent",
    agent_subtitle="Performs research and analysis for the selected company",
    enable_admin_access=True,
    header_height=85
)

shared = get_shared_data()
account = shared.get("account") or ""
industry = shared.get("industry") or ""
problem = shared.get("problem") or ""

st.session_state.current_account = account
st.session_state.current_industry = industry
st.session_state.current_problem = problem

def _norm_display(val, fallback):
    if not val or val in ("Select Account", "Select Industry", "Select Problem"):
        return fallback
    return val

display_account = _norm_display(account, "Unknown Company")
display_industry = _norm_display(industry, "Unknown Industry")

account, industry, problem = render_unified_business_inputs(
    page_key_prefix="company",
    show_titles=True,
    title_account_industry="Account & Industry",
    title_problem="Business Problem Description",
    save_button_label="Save Problem Details",
)

st.markdown("---")

has_account = account and account != "Select Account"
has_industry = industry and industry != "Select Industry"
has_problem = bool(problem.strip())

analyze_btn = st.button(
    "Analyze Company",
    type="primary",
    use_container_width=True,
    disabled=not (has_account and has_problem)
)

if analyze_btn:
    st.session_state.validation_attempted = True
    if not has_account or not has_industry or not has_problem:
        st.error("Please complete all inputs before proceeding.")
        st.stop()

    full_context = f"""
    Business Problem:
    {problem.strip()}

    Context:
    Account (Company): {account}
    Industry: {industry}
    """.strip()

    with st.spinner("Researching company • up to 3 minutes"):
        result = call_api("company_research", full_context, {})
        if result:
            st.session_state.company_output = result
            st.session_state.show_company = True
            st.session_state.analysis_complete = True
            st.success("Company research complete!")
        else:
            st.session_state.company_output = "No data returned"
            st.session_state.show_company = True
            st.error("Failed to retrieve data.")

# =========================================
# DISPLAY RESULTS
# =========================================
if st.session_state.get("show_company") and st.session_state.get("company_output"):
    st.markdown("---")

    st.markdown(
        f"""
        <div style="margin:20px 0;">
            <div class="section-title-box" style="padding:1rem 1.5rem; background:#0b5f8a; border-radius:12px;">
                <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; color:white;">
                    <h3 style="margin:0; font-weight:800; font-size:1.4rem;">Company Research</h3>
                    <p style="font-size:0.95rem; margin:8px 0 0; max-width:900px; text-align:center;">
                        AI-generated context for <strong>{display_account}</strong> in <strong>{display_industry}</strong>.<br>
                        Covers vision, operations, financials, and root causes — no solutions.
                    </p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    formatted_html = format_company_html(st.session_state.company_output)

    st.markdown(
        f"""
        <div style="background:var(--bg-card); border:2px solid #0b5f8a; 
                   border-radius:16px; padding:1.6rem; margin-bottom:1.6rem; 
                   box-shadow:0 3px 10px rgba(11,95,138,0.15);">
            <h4 style="color:#0b5f8a; font-weight:700; font-size:1.15rem; 
                      margin:0 0 1rem; border-bottom:2px solid #0b5f8a; 
                      padding-bottom:0.5rem;">
                Company Overview
            </h4>
            {formatted_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

    sections = parse_sections_from_output(st.session_state.company_output)
    employee_id = get_employee_id()

    if not st.session_state.get('company_feedback_submitted', False):
        fb_choice = st.radio(
            "Select your feedback type:",
            options=[
                "I have read it, found it useful, thanks.",
                "I have read it, found some facts or sections to be inaccurate.",
                "I have suggestions for improving the research output or format.",
            ],
            index=None,
            key="company_feedback_radio",
        )

        if fb_choice == "I have read it, found it useful, thanks.":
            with st.form("company_feedback_form_positive", clear_on_submit=True):
                st.markdown(f'**Employee ID:** {employee_id}')
                section = st.selectbox("Feedback for section:", options=sections, index=0)
                if st.form_submit_button("Submit Positive Feedback"):
                    submit_feedback(section, "Positive", employee_id, additional_feedback="Useful")
                    st.rerun()

        elif fb_choice == "I have read it, found some facts or sections to be inaccurate.":
            with st.form("company_feedback_form_inaccurate", clear_on_submit=True):
                st.markdown(f'**Employee ID:** {employee_id}')
                section = st.selectbox("Select Section", options=sections, index=0)
                inaccurate = st.text_area("Paste inaccurate excerpts (one per line):", height=140)
                additional = st.text_input("Additional comments:")
                if st.form_submit_button("Submit Feedback"):
                    if not inaccurate.strip() and not additional.strip():
                        st.warning("Please provide details.")
                    else:
                        off_defs = " | ".join([l.strip() for l in inaccurate.splitlines() if l.strip()]) or "No excerpts"
                        submit_feedback(section, "Inaccurate", employee_id, off_definitions=off_defs, additional_feedback=additional)
                        st.rerun()

        elif fb_choice == "I have suggestions for improving the research output or format.":
            with st.form("company_feedback_form_suggestions", clear_on_submit=True):
                st.markdown(f'**Employee ID:** {employee_id}')
                section = st.selectbox("Suggestion for section:", options=sections, index=0)
                suggestions = st.text_area("Your suggestions:", height=140)
                if st.form_submit_button("Submit Feedback"):
                    if suggestions.strip():
                        submit_feedback(section, "Suggestion", employee_id, suggestions=suggestions)
                        st.rerun()
                    else:
                        st.warning("Please provide suggestions.")

    else:
        st.markdown('<div class="feedback-success">Thank you! Your feedback has been recorded.</div>', unsafe_allow_html=True)
        if st.button("Submit Another Feedback", key="company_reopen_feedback_btn", use_container_width=True):
            st.session_state.company_feedback_submitted = False
            st.rerun()

    # =========================================
    # DOWNLOAD SECTION
    # =========================================
    if st.session_state.company_feedback_records or ('company_feedback_data' in st.session_state and not st.session_state.company_feedback_data.empty):
        st.markdown("---")
        st.markdown(
            """
            <div style="margin: 10px 0;">
                <div class="section-title-box" style="padding: 0.5rem 1rem;">
                    <div style="display:flex; flex-direction:column; align-items:center; justify-content:center;">
                        <h3 style="margin:0; color:white; font-weight:700; font-size:1.2rem;">Download Company Research</h3>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"company_research_{display_account.replace(' ', '_')}_{ts}.txt"

        buffer = io.StringIO()
        buffer.write("COMPANY RESEARCH REPORT\n")
        buffer.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        buffer.write(f"Company: {display_account}\n")
        buffer.write(f"Industry: {display_industry}\n\n")
        buffer.write("RESEARCH OUTPUT\n\n")
        buffer.write(st.session_state.company_output or "No output")

        st.download_button(
            "Download Company Research Report",
            data=buffer.getvalue(),
            file_name=filename,
            mime="text/plain",
            use_container_width=True
        )

# =========================================
# BACK BUTTON
# =========================================
st.markdown("---")
if st.button("Back to Main Page", use_container_width=True):
    st.switch_page("Welcome_Agent.py")