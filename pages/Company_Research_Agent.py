from shared_header import render_header

render_header(
    agent_name="Company Research Agent",
    agent_subtitle="Performs research and analysis for the selected company",
    enable_admin_access=True,
    header_height=85
)
import streamlit as st
import streamlit.components.v1 as components
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
    ACCOUNTS,
    INDUSTRIES,
    ACCOUNT_INDUSTRY_MAP,
    get_shared_data,
    render_unified_business_inputs,
    render_unified_admin_panel,
)

# --- Page Config ---
st.set_page_config(
    page_title="Company Research Agent",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Initialize session state ---
for key, default in {
    'company_output': "",
    'show_company': False,
    'company_feedback_submitted': False,
    'company_feedback_records': [],   # holds dicts of feedback entries in-session
    'feedback_option': None,
    'analysis_complete': False,
    'validation_attempted': False
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ===============================
# API Configuration
# ===============================
TENANT_ID = "talos"
HEADERS_BASE = {"Content-Type": "application/json"}

COMPANY_API_URL = (
    "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?society_id=1757657318406&agency_id=1762327921111&level=1"
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

# Feedback file
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
FEEDBACK_FILE = os.path.join(BASE_DIR, "feedback.csv")

# ===============================
# Auth Token
# ===============================
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

# ===============================
# Utility Functions
# ===============================
def json_to_text(data):
    if data is None:
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

# ===============================
# Enhanced API Call
# ===============================
def call_api(agent_name, problem, outputs):
    config = next((a for a in API_CONFIGS if a["name"] == agent_name), None)
    if not config:
        st.error("Invalid API configuration.")
        return None

    prompt = config["prompt"](problem, outputs)
    if isinstance(prompt, (list, tuple)):
        prompt = " ".join(prompt)
    payload = {"agency_goal": prompt}

    headers = HEADERS_BASE.copy()
    headers.update({"Tenant-ID": TENANT_ID, "X-Tenant-ID": TENANT_ID})
    if st.session_state.auth_token:
        headers["Authorization"] = f"Bearer {st.session_state.auth_token}"

    retries = 3
    for attempt in range(retries):
        try:
            response = requests.post(
                config["url"],
                headers=headers,
                json=payload,
                timeout=(15, 180)
            )

            if response.status_code == 200:
                return sanitize_text(json_to_text(response.json()))
            else:
                st.warning(f"Attempt {attempt+1}: API Error {response.status_code} - retrying...")
        except requests.exceptions.Timeout:
            st.warning(f"Attempt {attempt+1}: Timeout - retrying...")
        except Exception as e:
            st.warning(f"Attempt {attempt+1}: {str(e)} - retrying...")

    st.error("API request failed after 3 retries.")
    return None


def format_company_html(text):
    if not text:
        return "No company data available"
    t = sanitize_text(text)
    t = re.sub(r'(^|\n)\s*\*\s*', '\n• ', t)
    t = re.sub(r'^(Section\s+\d+:)\s*(.+)$', r'<strong>\1 \2</strong>', t, flags=re.MULTILINE | re.IGNORECASE)
    paragraphs = [f"<p style='margin:6px 0; line-height:1.45;'>{p}</p>" for p in t.split('\n\n') if p.strip()]
    return "\n".join(paragraphs)

# ===============================
# Feedback System (Extended)
# ===============================
def parse_sections_from_output(output_text):
    """
    Extracts Section headings (e.g. 'Section 1 — Company Understanding' or 'Section 1 — ...')
    and returns an ordered list of unique headings. If none found, return ['Full Report'].
    """
    if not output_text:
        return ["Full Report"]

    # Match "Section 1 — Title" or "Section 1 - Title" or "Section 1: Title"
    pattern = r'(Section\s+\d+\s*(?:[-—:])\s*.+)'
    matches = re.findall(pattern, output_text, flags=re.IGNORECASE)
    # fallback: also pick headings that look like "Section 1 — ..."
    matches = [m.strip() for m in matches]
    # dedupe preserving order
    seen = set()
    unique = []
    for m in matches:
        if m.lower() not in seen:
            seen.add(m.lower())
            unique.append(m)
    if not unique:
        return ["Full Report"]
    return unique

def get_user_id():
    # attempt session state first
    if 'employee_id' in st.session_state and st.session_state.employee_id:
        return st.session_state.employee_id
    possible_keys = ['user_id', 'userID', 'employee_id', 'EmployeeID']
    for key in possible_keys:
        if key in st.session_state and st.session_state[key]:
            return st.session_state[key]
    try:
        shared_data = get_shared_data()
        if shared_data and 'user_id' in shared_data:
            return shared_data['user_id']
        if shared_data and 'employee_id' in shared_data:
            return shared_data['employee_id']
    except Exception:
        pass
    return "Not Available"

def persist_feedback_to_csv(df):
    """
    Try to append to FEEDBACK_FILE; if file exists, ensure columns align.
    Return True on success, False otherwise.
    """
    try:
        if os.path.exists(FEEDBACK_FILE):
            existing = pd.read_csv(FEEDBACK_FILE)
            # ensure same columns
            missing = set(df.columns) - set(existing.columns)
            for c in missing:
                existing[c] = ''
            existing = existing[df.columns]
            updated = pd.concat([existing, df], ignore_index=True)
        else:
            updated = df

        updated.to_csv(FEEDBACK_FILE, index=False)
        return True
    except Exception:
        return False

def submit_feedback_record(section, feedback_type, user_id, off_definitions="", suggestions="", additional_feedback=""):
    """
    Central wrapper that saves feedback via save_feedback_to_admin_session and also attempts CSV persistence.
    It also appends feedback into st.session_state['company_feedback_records'] for immediate UI.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    account = st.session_state.get("current_account", "")
    industry = st.session_state.get("current_industry", "")
    problem_statement = st.session_state.get("current_problem", "")

    feedback_data = {
        "Employee_id": user_id,
        "Feedback": additional_feedback or "",
        "FeedbackType": feedback_type,
        "OffDefinitions": off_definitions or "",
        "Suggestions": suggestions or "",
        "Account": account,
        "Industry": industry,
        "ProblemStatement": problem_statement,
        "Section": section,
        "Timestamp": timestamp
    }

    # send to admin session helper (your existing)
    try:
        save_feedback_to_admin_session(feedback_data, "Company Research Agent")
    except Exception:
        # ignore admin session failure but continue
        pass

    # prepare DataFrame row for CSV
    df = pd.DataFrame([[
        timestamp,
        user_id,
        additional_feedback or "",
        feedback_type,
        off_definitions or "",
        suggestions or "",
        account,
        industry,
        problem_statement,
        section
    ]], columns=["Timestamp","Employee_id","Feedback","FeedbackType","OffDefinitions","Suggestions","Account","Industry","ProblemStatement","Section"])

    saved = persist_feedback_to_csv(df)
    if not saved:
        # fallback: store in session
        if 'company_feedback_data' not in st.session_state:
            st.session_state.company_feedback_data = pd.DataFrame(columns=df.columns)
        st.session_state.company_feedback_data = pd.concat([st.session_state.company_feedback_data, df], ignore_index=True)
        st.info("📝 Feedback stored in session (couldn't write to disk).")

    # append to in-memory records for UI
    st.session_state.company_feedback_records.append(feedback_data)
    st.session_state.company_feedback_submitted = True
    return True

# ===============================
# Main UI
# ===============================
shared = get_shared_data()
account = shared.get("account") or ""
industry = shared.get("industry") or ""
problem = shared.get("problem") or ""

st.session_state.current_account = account
st.session_state.current_industry = industry
st.session_state.current_problem = problem

account, industry, problem = render_unified_business_inputs(
    page_key_prefix="company",
    show_titles=True,
    title_account_industry="Account & Industry",
    title_problem="Business Problem Description",
    save_button_label="✅ Save Problem Details",
)

st.markdown("---")

has_account = account and account != "Select Account"
has_industry = industry and industry != "Select Industry"
has_problem = bool(problem.strip())

extract_btn = st.button("🏢 Analyze Company", type="primary", use_container_width=True,
                        disabled=not (has_account and has_problem))

if extract_btn:
    st.session_state.validation_attempted = True
    if not has_account or not has_industry or not has_problem:
        st.error("❌ Please complete all inputs before proceeding.")
        st.stop()

    full_context = f"""
    Business Problem:
    {problem.strip()}

    Context:
    Account (Company): {account}
    Industry: {industry}
    """.strip()

    with st.spinner("🏢 Researching company details • ⏱️ up to 3 minutes"):
        result = call_api("company_research", full_context, {})
        if result:
            st.session_state.company_output = result
            st.session_state.show_company = True
            st.session_state.analysis_complete = True
            st.success("✅ Company research complete!")
        else:
            st.session_state.company_output = "API Error or no data returned"
            st.session_state.show_company = True
            st.error("API request failed or no data returned")

# ===============================
# Display Results + Feedback UI
# ===============================
if st.session_state.get("show_company") and st.session_state.get("company_output"):
    st.markdown("---")
    display_account = account or "Unknown Company"
    display_industry = industry or "Unknown Industry"

    st.markdown(
        f"""
        <div style="margin: 20px 0;">
            <div class="section-title-box" style="padding: 1rem 1.5rem;">
                <div style="display:flex; flex-direction:column; align-items:center; justify-content:center;">
                    <h3 style="margin-bottom:8px; color:white; font-weight:800; font-size:1.4rem;">Company Research</h3>
                    <p style="font-size:0.95rem; color:white; margin:0; line-height:1.5; text-align:center; max-width: 900px;">
                        AI-generated company context for <strong>{display_account}</strong> in <strong>{display_industry}</strong>.
                        This focuses on company vision, structure, operations, and financial performance — no solutions provided.
                    </p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    formatted = format_company_html(st.session_state.company_output)

    st.markdown(
        f"""
        <div style="
            background: var(--bg-card);
            border: 2px solid #0b5f8a;
            border-radius: 12px;
            padding: 1.6rem;
            margin-bottom: 1.6rem;
        ">
            <h4 style="color: #0b5f8a; font-weight:700; font-size:1.1rem; margin:0 0 1rem 0;">Company Overview</h4>
            <div style="color: var(--text-primary); line-height:1.4; font-size:0.98rem; text-align:left;">
                {formatted}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # -------------------------
    # Parse sections for feedback
    # -------------------------
    sections = parse_sections_from_output(st.session_state.company_output)

    st.markdown("---")
    st.markdown('<div class="section-title-box" style="text-align:center;"><h3>💬 User Feedback</h3></div>', unsafe_allow_html=True)
    st.markdown("Please share your thoughts or suggestions after reviewing the company research results.")

    user_id = get_user_id()

    # If no feedback submitted yet, show the forms
    if not st.session_state.get('company_feedback_submitted', False):
        fb_choice = st.radio(
            "Select your feedback type:",
            options=[
                "I have read it, found it useful, thanks.",
                "I have read it, found some facts or sections to be inaccurate.",
                "I have suggestions for improving the research output or format.",
            ],
            key="company_feedback_radio",
        )
        st.session_state.feedback_option = fb_choice

        if fb_choice == "I have read it, found it useful, thanks.":
            with st.form("company_feedback_form_positive", clear_on_submit=True):
                st.info("Thank you for your positive feedback!")
                st.markdown(f'**Employee ID:** {user_id}')
                section_choice = st.selectbox("Which section is this feedback for?", options=sections, index=0)
                submitted = st.form_submit_button("📨 Submit Positive Feedback")
                if submitted:
                    submit_feedback_record(section=section_choice, feedback_type="Positive", user_id=user_id, additional_feedback="User indicated positive feedback.")

        elif fb_choice == "I have read it, found some facts or sections to be inaccurate.":
            with st.form("company_feedback_form_inaccurate", clear_on_submit=True):
                st.markdown("**Please indicate which sections or statements seem inaccurate:**")
                st.markdown(f'**Employee ID:** {user_id}')
                section_choice = st.selectbox("Select Section", options=sections, index=0)
                # allow selecting multiple problematic lines/phrases
                inaccurate_text = st.text_area("Paste excerpts or list inaccuracies (one per line):", height=140)
                additional = st.text_input("Additional comments (optional):")
                submitted = st.form_submit_button("📨 Submit Feedback")
                if submitted:
                    if not inaccurate_text.strip() and not additional.strip():
                        st.warning("⚠️ Please provide details on inaccuracies or comments.")
                    else:
                        # condense the inaccuracies
                        off_defs_text = " | ".join([line.strip() for line in inaccurate_text.splitlines() if line.strip()]) or "No excerpts provided"
                        submit_feedback_record(section=section_choice, feedback_type="Inaccurate/Issue", user_id=user_id, off_definitions=off_defs_text, additional_feedback=additional)
                        st.rerun()

        elif fb_choice == "I have suggestions for improving the research output or format.":
            with st.form("company_feedback_form_suggestions", clear_on_submit=True):
                st.markdown("**Please share your suggestions:**")
                st.markdown(f'**Employee ID:** {user_id}')
                section_choice = st.selectbox("Which section is your suggestion about?", options=sections, index=0, key="company_sugg_section")
                suggestions = st.text_area("Your suggestions:", height=140)
                submitted = st.form_submit_button("📨 Submit Feedback")
                if submitted:
                    if not suggestions.strip():
                        st.warning("⚠️ Please provide your suggestions.")
                    else:
                        submit_feedback_record(section=section_choice, feedback_type="Suggestion", user_id=user_id, suggestions=suggestions, additional_feedback=suggestions)
                        st.rerun()

    else:
        # Already submitted - show success and option to submit another
        st.markdown('<div class="feedback-success">✅ Thank you! Your feedback has been recorded.</div>', unsafe_allow_html=True)
        if st.button("📝 Submit Another Feedback", key="company_reopen_feedback_btn", use_container_width=True):
            st.session_state.company_feedback_submitted = False
            st.rerun()

    # -------------------------
    # Download Report (enabled when any feedback exists)
    # -------------------------
    if st.session_state.company_feedback_records or ('company_feedback_data' in st.session_state and not st.session_state.company_feedback_data.empty):
        st.markdown("---")
        st.markdown(
            """
            <div style="margin: 10px 0;">
                <div class="section-title-box" style="padding: 0.5rem 1rem;">
                    <div style="display:flex; flex-direction:column; align-items:center; justify-content:center;">
                        <h3 style="margin:0; color:white; font-weight:700; font-size:1.2rem; line-height:1.2;">📥 Download Company Research </h3>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # build download contents
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"company_research_{display_account.replace(' ','_')}_{ts}.txt" if display_account else f"company_research_{ts}.txt"

        download_buffer = io.StringIO()
        download_buffer.write("COMPANY RESEARCH REPORT\n")
        download_buffer.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        download_buffer.write(f"Company: {display_account}\n")
        download_buffer.write(f"Industry: {display_industry}\n\n")
        download_buffer.write("---- RESEARCH OUTPUT ----\n\n")
        download_buffer.write(st.session_state.company_output or "No output\n")


        st.download_button(
            "⬇️ Download Company Research Report",
            data=download_buffer.getvalue(),
            file_name=filename,
            mime="text/plain",
            use_container_width=True
        )

# ===============================
# Back Button
# ===============================
st.markdown("---")
if st.button("⬅️ Back to Main Page", use_container_width=True):
    st.switch_page("Welcome_Agent.py")
