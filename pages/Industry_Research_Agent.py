from shared_header import render_header

render_header(
    agent_name="Industry Research Agent",
    agent_subtitle="Performs research and analysis for the selected industry",
    enable_admin_access=True,
    header_height=85
)
import streamlit as st
import streamlit.components.v1 as components
import os
import re
import json
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
    page_title="Industry Research Agent",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Initialize session state ---
if 'industry_output' not in st.session_state:
    st.session_state.industry_output = ""
if 'show_industry' not in st.session_state:
    st.session_state.show_industry = False
if 'industry_feedback_submitted' not in st.session_state:
    st.session_state.industry_feedback_submitted = False
if 'feedback_option' not in st.session_state:
    st.session_state.feedback_option = None
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'validation_attempted' not in st.session_state:
    st.session_state.validation_attempted = False

# ===============================
# API Configuration
# ===============================

TENANT_ID = "talos"
HEADERS_BASE = {"Content-Type": "application/json"}

INDUSTRY_API_URL = "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?society_id=1757657318406&agency_id=1762325261936&level=1"

API_CONFIGS = [
    {
        "name": "industry_research",
        "url": INDUSTRY_API_URL,
        "multiround_convo": 3,
        "description": "industry research",
        "prompt": lambda problem, outputs: (
            f"{problem}\n\nExplore and document the industry connected to the above problem statement.\n" \
            "Cover operations, market structure, customers, competitive landscape, supply chain, regulatory environment, trends, demand drivers, key players, and external forces.\n" \
            "Do not propose solutions. Stick to facts, context, and explanations that help understand the ecosystem.\n"
        )
    }
]

# Global feedback file path
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
FEEDBACK_FILE = os.path.join(BASE_DIR, "feedback.csv")

# Token initialization
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
# Utility Functions (reused/adapted)
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


def call_api(agent_name, problem, outputs):
    config = next((a for a in API_CONFIGS if a["name"] == agent_name), None)
    if not config:
        st.error("Invalid API configuration.")
        return None

    prompt = config["prompt"](problem, outputs)
    payload = {"agency_goal": prompt}

    headers = HEADERS_BASE.copy()
    headers.update({"Tenant-ID": TENANT_ID, "X-Tenant-ID": TENANT_ID})
    if 'auth_token' in st.session_state and st.session_state.auth_token:
        headers["Authorization"] = f"Bearer {st.session_state.auth_token}"

    try:
        response = requests.post(config["url"], headers=headers, json=payload, timeout=60)
        if response.status_code == 200:
            return sanitize_text(json_to_text(response.json()))
        else:
            st.error(f"API Error: {response.status_code} - {response.text[:200]}")
            return None
    except Exception as e:
        st.error(f"API Call Failed: {str(e)}")
        return None


def format_industry_html(text):
    if not text:
        return "No industry data available"
    t = sanitize_text(text)
    # Simple formatting: convert bullets, bold headers
    t = re.sub(r'(^|\n)\s*\*\s*', '\n• ', t)
    t = re.sub(r'^(Section\s+\d+:)\s*(.+)$', r'<strong>\1 \2</strong>', t, flags=re.MULTILINE|re.IGNORECASE)
    paragraphs = [f"<p style='margin:6px 0; line-height:1.45;'>{p}</p>" for p in t.split('\n\n') if p.strip()]
    return "\n".join(paragraphs)


def submit_feedback(feedback_type, employee_id="", off_definitions="", suggestions="", additional_feedback=""):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    account = st.session_state.get("current_account", "")
    industry = st.session_state.get("current_industry", "")
    problem_statement = st.session_state.get("current_problem", "")

    feedback_data = {
        "Employee_id": employee_id,
        "Feedback": additional_feedback,
        "FeedbackType": feedback_type,
        "OffDefinitions": off_definitions,
        "Suggestions": suggestions,
        "Account": account,
        "Industry": industry,
        "ProblemStatement": problem_statement
    }

    save_feedback_to_admin_session(feedback_data, "Industry Research Agent")

    new_entry = pd.DataFrame([[
        timestamp, employee_id ,additional_feedback, feedback_type, off_definitions, suggestions, account, industry, problem_statement
    ]], columns=["Timestamp","Employee_id", "Feedback", "FeedbackType", "OffDefinitions", "Suggestions", "Account", "Industry", "ProblemStatement"])

    try:
        if os.path.exists(FEEDBACK_FILE):
            existing = pd.read_csv(FEEDBACK_FILE)
            missing_cols = set(new_entry.columns) - set(existing.columns)
            for col in missing_cols:
                existing[col] = ''
            existing = existing[new_entry.columns]
            updated = pd.concat([existing, new_entry], ignore_index=True)
        else:
            updated = new_entry

        try:
            updated.to_csv(FEEDBACK_FILE, index=False)
        except (PermissionError, OSError):
            if 'feedback_data' not in st.session_state:
                st.session_state.feedback_data = pd.DataFrame(columns=new_entry.columns)
            st.session_state.feedback_data = pd.concat([st.session_state.feedback_data, new_entry], ignore_index=True)
            st.info("📝 Feedback saved to session (cloud mode)")

        st.session_state.industry_feedback_submitted = True
        return True
    except Exception as e:
        st.error(f"Error saving feedback: {str(e)}")
        return False


def reset_app_state():
    keys_to_clear = ['industry_output', 'show_industry', 'industry_feedback_submitted', 'feedback_option', 'analysis_complete', 'validation_attempted']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    st.success("✅ Application reset successfully! You can start a new analysis.")

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

account, industry, problem = render_unified_business_inputs(
    page_key_prefix="industry",
    show_titles=True,
    title_account_industry="Account & Industry",
    title_problem="Business Problem Description",
    save_button_label="✅ Save Problem Details",
)

st.markdown("---")

has_account = account and account != "Select Account"
has_industry = industry and industry != "Select Industry"
has_problem = bool(problem.strip())

extract_btn = st.button("🔎 Explore Industry", type="primary", use_container_width=True,
                        disabled=not (has_account and has_industry and has_problem))

if extract_btn:
    st.session_state.validation_attempted = True
    if not has_account:
        st.error("❌ Please select an account before proceeding.")
        st.stop()
    if not has_industry:
        st.error("❌ Please select an industry before proceeding.")
        st.stop()
    if not has_problem:
        st.error("❌ Please enter a business problem description.")
        st.stop()

    full_context = f"""
    Business Problem:
    {problem.strip()}

    Context:
    Account: {account}
    Industry: {industry}
    """.strip()

    headers = HEADERS_BASE.copy()
    headers.update({"Tenant-ID": TENANT_ID, "X-Tenant-ID": TENANT_ID})
    if st.session_state.auth_token:
        headers["Authorization"] = f"Bearer {st.session_state.auth_token}"

    with st.spinner("🔎 Researching industry and assembling context • ⏱️ up to 90s"):
        try:
            outputs = {}
            result = call_api("industry_research", full_context, outputs)
            if result:
                st.session_state.industry_output = result
                st.session_state.show_industry = True
                st.session_state.analysis_complete = True
                st.success("✅ Industry research complete!")
            else:
                st.session_state.industry_output = "API Error or no data returned"
                st.session_state.show_industry = True
                st.error("API request failed or no data returned")
        except requests.exceptions.Timeout:
            st.session_state.industry_output = "Request timeout: The API took too long to respond."
            st.session_state.show_industry = True
            st.error("Request timeout - please try again.")
        except requests.exceptions.ConnectionError:
            st.session_state.industry_output = "Connection error: Unable to connect to the API server."
            st.session_state.show_industry = True
            st.error("Connection error - please check your network connection.")
        except Exception as e:
            st.session_state.industry_output = f"Unexpected error: {str(e)}"
            st.session_state.show_industry = True
            st.error(f"An unexpected error occurred: {str(e)}")

# Display results
if st.session_state.get("show_industry") and st.session_state.get("industry_output"):
    st.markdown("---")
    display_account = account or "Unknown Company"
    display_industry = industry or "Unknown Industry"

    st.markdown(
        f"""
        <div style="margin: 20px 0;">
            <div class="section-title-box" style="padding: 1rem 1.5rem;">
                <div style="display:flex; flex-direction:column; align-items:center; justify-content:center;">
                    <h3 style="margin-bottom:8px; color:white; font-weight:800; font-size:1.4rem; line-height:1.2;">
                        Industry Research
                    </h3>
                    <p style="font-size:0.95rem; color:white; margin:0; line-height:1.5; text-align:center; max-width: 900px;">
                        AI-generated industry context for <strong>{display_account}</strong> in <strong>{display_industry}</strong> based on your problem statement. This focuses on factual context and ecosystem mapping — no solutions provided.
                    </p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    formatted = format_industry_html(st.session_state.industry_output)

    st.markdown(
        f"""
        <div style="
            background: var(--bg-card);
            border: 2px solid #0b5f8a;
            border-radius: 12px;
            padding: 1.6rem;
            margin-bottom: 1.6rem;
        ">
            <h4 style="color: #0b5f8a; font-weight:700; font-size:1.1rem; margin:0 0 1rem 0;">Industry Overview</h4>
            <div style="color: var(--text-primary); line-height:1.4; font-size:0.98rem; text-align:left;">
                {formatted}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# Feedback section
if st.session_state.get("show_industry") and st.session_state.get("industry_output"):
    st.markdown("---")
    st.markdown('<div class="section-title-box" style="text-align:center;"><h3>💬 User Feedback</h3></div>', unsafe_allow_html=True)
    st.markdown("Please share your thoughts or suggestions after reviewing the industry research results.")

    def get_user_id():
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
        except:
            pass
        return 'Not Available'

    user_id = get_user_id()

    if not st.session_state.get('industry_feedback_submitted', False):
        fb_choice = st.radio(
            "Select your feedback type:",
            options=[
                "I have read it, found it useful, thanks.",
                "I have read it, found some facts or sections to be inaccurate.",
                "I have suggestions for improving the research output or format.",
            ],
            key="industry_feedback_radio",
        )

        if fb_choice:
            st.session_state.feedback_option = fb_choice

        if fb_choice == "I have read it, found it useful, thanks.":
            with st.form("industry_feedback_form_positive", clear_on_submit=True):
                st.info("Thank you for your positive feedback!")
                st.markdown(f'**Employee ID:** {user_id}')
                submitted = st.form_submit_button("📨 Submit Positive Feedback")
                if submitted:
                    if submit_feedback(fb_choice, employee_id=user_id):
                        st.rerun()

        elif fb_choice == "I have read it, found some facts or sections to be inaccurate.":
            with st.form("industry_feedback_form_inaccurate", clear_on_submit=True):
                st.markdown("**Please indicate which sections or statements seem inaccurate:**")
                st.markdown(f'**Employee ID:** {user_id}')
                inaccuracies = st.text_area("List inaccuracies or paste excerpts:", height=120, key="industry_inaccuracies_input")
                additional = st.text_input("Additional comments (optional):", key="industry_additional_comments")
                submitted = st.form_submit_button("📨 Submit Feedback")
                if submitted:
                    if not inaccuracies.strip() and not additional.strip():
                        st.warning("⚠️ Please provide details on inaccuracies or comments.")
                    else:
                        if submit_feedback(fb_choice, employee_id=user_id, off_definitions=inaccuracies, additional_feedback=additional):
                            st.rerun()

        elif fb_choice == "I have suggestions for improving the research output or format.":
            with st.form("industry_feedback_form_suggestions", clear_on_submit=True):
                st.markdown("**Please share your suggestions:**")
                st.markdown(f'**Employee ID:** {user_id}')
                suggestions = st.text_input("Your suggestions:", key="industry_suggestions_input")
                submitted = st.form_submit_button("📨 Submit Feedback")
                if submitted:
                    if not suggestions.strip():
                        st.warning("⚠️ Please provide your suggestions.")
                    else:
                        if submit_feedback(fb_choice, employee_id=user_id, suggestions=suggestions):
                            st.rerun()
    else:
        st.markdown('<div class="feedback-success">✅ Thank you! Your feedback has been recorded.</div>', unsafe_allow_html=True)
        if st.button("📝 Submit Another Feedback", key="industry_reopen_feedback_btn", use_container_width=True):
            st.session_state.industry_feedback_submitted = False
            st.rerun()

# Download Section
if st.session_state.get('industry_feedback_submitted', False):
    st.markdown("---")
    st.markdown(
        """
        <div style="margin: 10px 0;">
            <div class="section-title-box" style="padding: 0.5rem 1rem;">
                <div style="display:flex; flex-direction:column; align-items:center; justify-content:center;">
                    <h3 style="margin:0; color:white; font-weight:700; font-size:1.2rem; line-height:1.2;">📥 Download Industry Research</h3>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    industry_text = st.session_state.get("industry_output", "")
    if industry_text and not industry_text.startswith("API Error") and not industry_text.startswith("Error:"):
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"industry_research_{display_account.replace(' ', '_')}_{ts}.txt" if 'display_account' in globals() else f"industry_research_{ts}.txt"
        download_content = f"""Industry Research Export
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Company: {account}
Industry: {industry}

{industry_text}

---
Generated by Industry Research Agent
"""
        st.download_button(
            "⬇️ Download Industry Research as Text File",
            data=download_content,
            file_name=filename,
            mime="text/plain",
            use_container_width=True
        )
    else:
        st.info("No industry research available for download. Please complete the analysis first.")

# Back button
st.markdown("---")
if st.button("⬅️ Back to Main Page", use_container_width=True):
    st.switch_page("Welcome_Agent.py")
