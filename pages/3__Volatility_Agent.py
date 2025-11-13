# pip install markdown2 requests pandas

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
    save_feedback_to_file,
    ACCOUNTS,
    INDUSTRIES,
    ACCOUNT_INDUSTRY_MAP,
    get_shared_data,
    render_unified_business_inputs,
    render_unified_admin_panel,
)

# =========================================
# PAGE CONFIG
# =========================================
st.set_page_config(
    page_title="Volatility Agent",
    layout="wide",
    initial_sidebar_state="collapsed"
    
)
hide_sidebar = """
    <style>
        [data-testid="stSidebar"] {display: none;}
    </style>
"""
st.markdown(hide_sidebar, unsafe_allow_html=True)

# =========================================
# SESSION INITIALIZATION - AGENT-SPECIFIC
# =========================================
session_defaults = {
    'volatile_outputs': {},
    'show_volatility': False,
    'feedback_submitted': False,
    'feedback_option': None,
    'analysis_complete': False,
    'validation_attempted': False,
    'volatility_feedback_submitted': False,
}

for key, val in session_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# =========================================
# API CONFIGURATION
# =========================================
TENANT_ID = "talos"
HEADERS_BASE = {"Content-Type": "application/json"}

vocab_output = st.session_state.get('vocab_output', '')
current_system_output = st.session_state.get('current_system_data', '')

API_CONFIGS = [
    {
        "name": "Q1",
        "url": "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?society_id=1757657318406&agency_id=1758555344231&level=1",
        "multiround_convo": 2,
        "description": "What is the frequency and pace of change in the key inputs driving the business?",
        "prompt": lambda problem, outputs: (
            f"Problem statement - {problem}\n\n"
            f"Context from vocabulary:\n{vocab_output}\n\n"
            f"Context from current system:\n{current_system_output}\n\n"
            "What is the frequency and pace of change in the key inputs driving the business? Provide detailed analysis, score 0–5, and justification."
        )
    },
    {
        "name": "Q2",
        "url": "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?society_id=1757657318406&agency_id=1758549615986&level=1",
        "multiround_convo": 2,
        "description": "To what extent are these changes cyclical and predictable versus sporadic and unpredictable?",
        "prompt": lambda problem, outputs: (
            f"Problem statement - {problem}\n\n"
            f"Context from vocabulary:\n{vocab_output}\n\n"
            f"Context from current system:\n{current_system_output}\n\n"
            "To what extent are these changes cyclical and predictable versus sporadic and unpredictable? "
            "Provide detailed analysis, score 0–5, and justification."
        )
    },
    {
        "name": "Q3",
        "url": "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?society_id=1757657318406&agency_id=1758614550482&level=1",
        "multiround_convo": 2,
        "description": "How resilient is the current system in absorbing these changes without requiring significant rework or disruption?",
        "prompt": lambda problem, outputs: (
            f"Problem statement - {problem}\n\n"
            f"Context from vocabulary:\n{vocab_output}\n\n"
            f"Context from current system:\n{current_system_output}\n\n"
            "How resilient is the current system in absorbing these changes without requiring significant rework or disruption? "
            "Provide detailed analysis, score 0–5, and justification."
        )
    }
]

# =========================================
# FILE CONFIG
# =========================================
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
FEEDBACK_FILE = os.path.join(BASE_DIR, "feedback.csv")

try:
    if not os.path.exists(FEEDBACK_FILE):
        df = pd.DataFrame(columns=[
            "Timestamp", "employee_id", "Feedback", "FeedbackType", 
            "OffDefinitions", "Suggestions", "Account", "Industry", "ProblemStatement"
        ])
        df.to_csv(FEEDBACK_FILE, index=False)
except (PermissionError, OSError):
    if 'feedback_data' not in st.session_state:
        st.session_state.feedback_data = pd.DataFrame(
            columns=["Timestamp", "employee_id", "Feedback", "FeedbackType", 
                    "OffDefinitions", "Suggestions", "Account", "Industry", "ProblemStatement"])

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
# ENHANCED FORMATTING FUNCTION (WITH BULLET CONVERSION FOR >2 LINES)
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
    text = re.sub(r'& Key Takeaway:', 'Key Takeaway:', text)
    return text.strip()

def format_volatility_with_bold(text, extra_phrases=None):
    """Enhanced formatting: Bold headings + Convert >2 line blocks to bullet points"""
    if not text:
        return "No volatility data available"

    clean_text = sanitize_text(text)
    clean_text = clean_text.replace(" - ", " : ")
    clean_text = re.sub(r'(?m)^\s*[-*]\s+', '• ', clean_text)

    extra_patterns = []
    if extra_phrases:
        for p in extra_phrases:
            if any(ch in p for ch in r".^$*+?{}[]\|()"):
                extra_patterns.append(p)
            else:
                extra_patterns.append(re.escape(p))

    lines = clean_text.splitlines()
    n = len(lines)
    i = 0
    paragraph_html = []

    def collect_continuation(start_idx):
        block_lines = [lines[start_idx].rstrip()]
        j = start_idx + 1
        while j < n:
            next_line = lines[j]
            if not next_line.strip():
                break
            if re.match(r'^\s+', next_line) or re.match(r'^\s*[a-z]', next_line):
                block_lines.append(next_line.rstrip())
                j += 1
                continue
            if re.match(r'^\s*(?:•|-|\d+\.)\s+', next_line):
                break
            break
        return block_lines, j

    while i < n:
        ln = lines[i].rstrip()
        if not ln.strip():
            paragraph_html.append('')
            i += 1
            continue

        if extra_patterns:
            new_ln = ln
            for pat in extra_patterns:
                try:
                    new_ln = re.sub(
                        pat, lambda m: f"<strong>{m.group(0)}</strong>", new_ln, flags=re.IGNORECASE)
                except re.error:
                    new_ln = re.sub(re.escape(pat), lambda m: f"<strong>{m.group(0)}</strong>", new_ln, flags=re.IGNORECASE)
            if new_ln != ln:
                paragraph_html.append(new_ln)
                i += 1
                continue

        # Step headings
        if re.search(r'(Step\s*\d+\s*:)', ln, flags=re.IGNORECASE):
            block, j = collect_continuation(i)
            block_text = "<br>".join([b.strip() for b in block])
            paragraph_html.append(f"<strong>{block_text}</strong>")
            i = j
            continue

        # Numbered with colon
        m_num_colon = re.match(r'^\s*(\d+\.\s+[^:]+):\s*(.*)$', ln)
        if m_num_colon:
            heading = m_num_colon.group(1).strip()
            remainder = m_num_colon.group(2).strip()
            paragraph_html.append(
                f"<strong>{heading}:</strong> {remainder}" if remainder else f"<strong>{heading}:</strong>")
            i += 1
            continue

        # Numbered without colon → collect block
        m_num_no_colon = re.match(r'^\s*(\d+\.\s+.+)$', ln)
        if m_num_no_colon:
            block, j = collect_continuation(i)
            block_lines = [b.strip() for b in block if b.strip()]
            if len(block_lines) > 1:
                # Convert to bullets if >1 line
                bullet_items = [f"• {line}" for line in block_lines[1:]]
                paragraph_html.append(f"<strong>{block_lines[0]}</strong>")
                paragraph_html.extend(bullet_items)
            else:
                paragraph_html.append(f"<strong>{block_lines[0]}</strong>")
            i = j
            continue

        # Bullet with colon
        m_bullet_heading = re.match(r'^\s*(?:•|\d+\.)\s*([^:]+):\s*(.*)$', ln)
        if m_bullet_heading:
            heading = m_bullet_heading.group(1).strip()
            remainder = m_bullet_heading.group(2).strip()
            paragraph_html.append(
                f"• <strong>{heading}:</strong> {remainder}" if remainder else f"• <strong>{heading}:</strong>")
            i += 1
            continue

        # Generic "Key: Value"
        m_side = re.match(r'^\s*([^:]+):\s*(.*)$', ln)
        if m_side and len(m_side.group(1).split()) <= 8:
            left = m_side.group(1).strip()
            right = m_side.group(2).strip()
            paragraph_html.append(
                f"<strong>{left}:</strong> {right}" if right else f"<strong>{left}:</strong>")
            i += 1
            continue

        if re.fullmatch(r'\s*Revenue\s+Growth\s+Rate\s*', ln, flags=re.IGNORECASE):
            paragraph_html.append(f"<strong>{ln.strip()}</strong>")
            i += 1
            continue

        # NEW: Detect multi-line paragraph blocks and convert to bullets if >2 lines
        if not re.match(r'^\s*(•|\d+\.|[-*]|\s*<strong>)', ln):
            block, j = collect_continuation(i)
            block_lines = [b.strip() for b in block if b.strip()]
            if len(block_lines) > 2:
                # Convert to bullet points
                for idx, line in enumerate(block_lines):
                    if idx == 0:
                        paragraph_html.append(f"<strong>{line}</strong>")
                    else:
                        paragraph_html.append(f"• {line}")
                i = j
                continue
            else:
                # Keep as paragraph
                paragraph_html.append("<br>".join(block_lines))
                i = j
                continue

        paragraph_html.append(ln)
        i += 1

    # Group into final paragraphs
    final_paragraphs = []
    temp_lines = []
    for entry in paragraph_html:
        if entry == '':
            if temp_lines:
                final_paragraphs.append("<br>".join(temp_lines))
                temp_lines = []
        else:
            temp_lines.append(entry)
    if temp_lines:
        final_paragraphs.append("<br>".join(temp_lines))

    para_wrapped = [
        f"<p style='margin:6px 0; line-height:1.45; font-size:0.98rem;'>{p}</p>" for p in final_paragraphs
    ]
    final_html = "\n".join(para_wrapped)

    # Final cleanup
    final_html = re.sub(r'(<br>\s*){3,}', '<br><br>', final_html)
    return final_html

# =========================================
# API CALL & FEEDBACK FUNCTIONS
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

def submit_feedback(feedback_type, employee_id="", off_definitions="", suggestions="", additional_feedback=""):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    account = st.session_state.get("current_account", "")
    industry = st.session_state.get("current_industry", "")
    problem_statement = st.session_state.get("current_problem", "")
    
    columns = ["Timestamp", "Employee_id", "Feedback", "FeedbackType",
               "OffDefinitions", "Suggestions", "Account", "Industry", "ProblemStatement"]
    
    row = [timestamp, employee_id, additional_feedback, feedback_type,
           off_definitions, suggestions, account, industry, problem_statement]
    
    entry = pd.DataFrame([row], columns=columns)
    admin_data = { "Employee_id": employee_id, "Feedback": additional_feedback, "FeedbackType": feedback_type,
                  "OffDefinitions": off_definitions, "Suggestions": suggestions,
                  "Account": account, "Industry": industry, "ProblemStatement": problem_statement }
    save_feedback_to_admin_session(admin_data, "Volatility Agent")
    
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
        if "feedback_data" not in st.session_state:
            st.session_state.feedback_data = pd.DataFrame(columns=columns)
        st.session_state.feedback_data = pd.concat([st.session_state.feedback_data, entry], ignore_index=True)
    
    st.session_state.volatility_feedback_submitted = True
    return True

def reset_app_state():
    keys_to_clear = ['volatile_outputs', 'show_volatility', 'feedback_submitted',
                     'feedback_option', 'analysis_complete', 'validation_attempted',
                     'volatility_feedback_submitted']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    st.success("Application reset successfully!")

# =========================================
# UI RENDERING
# =========================================
render_header(
    agent_name="Volatility Agent",
    agent_subtitle="Analyzing volatility and variability factors in your business problem.",
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
    page_key_prefix="volatility",
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
    "Analyze Volatility", 
    type="primary", 
    use_container_width=True,
    disabled=not (has_account and has_industry and has_problem)
)

if analyze_btn:
    st.session_state.validation_attempted = True
    if not has_account:
        st.error("Please select an account before proceeding.")
        st.stop()
    if not has_industry:
        st.error("Please select an industry before proceeding.")
        st.stop()
    if not has_problem:
        st.error("Please enter a business problem description.")
        st.stop()
    
    with st.spinner("Analyzing volatility and variability factors..."):
        progress = st.progress(0)
        st.session_state.volatile_outputs = {}
        total_apis = len(API_CONFIGS)
        
        for i, api_cfg in enumerate(API_CONFIGS):
            progress.progress(i / total_apis)
            outputs = {
                "vocabulary": st.session_state.get("vocab_output", ""),
                "current_system": st.session_state.get("current_system_data", ""),
            }
            result = call_api(api_cfg["name"], problem, outputs)
            st.session_state.volatile_outputs[api_cfg["name"]] = result if result else "No data available"
        
        progress.progress(1.0)
        st.session_state.show_volatility = True
        st.session_state.analysis_complete = True
        st.success("Volatility analysis complete!")

# =========================================
# DISPLAY RESULTS
# =========================================
if st.session_state.get("show_volatility") and st.session_state.get("volatile_outputs"):
    st.markdown("---")
    
    st.markdown(
        f"""
        <div style="margin:20px 0;">
            <div class="section-title-box" style="padding:1rem 1.5rem; background:#8b1e1e; border-radius:12px;">
                <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; color:white;">
                    <h3 style="margin:0; font-weight:800; font-size:1.4rem;">Volatility Analysis</h3>
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
    
    for api_name, api_output in st.session_state.volatile_outputs.items():
        if api_output and api_output != "No data available":
            api_desc = next((cfg["description"] for cfg in API_CONFIGS if cfg["name"] == api_name), api_name)
            formatted_html = format_volatility_with_bold(api_output)
            
            if display_account != "Unknown Company":
                formatted_html = re.sub(r'\bthe company\b', display_account, formatted_html, flags=re.IGNORECASE)
            if display_industry != "Unknown Industry":
                formatted_html = re.sub(r'\bthe industry\b', display_industry, formatted_html, flags=re.IGNORECASE)
            
            st.markdown(
                f"""
                <div style="background:var(--bg-card); border:2px solid #8b1e1e; 
                           border-radius:16px; padding:1.6rem; margin-bottom:1.6rem; 
                           box-shadow:0 3px 10px rgba(139,30,30,0.15);">
                    <h4 style="color:#8b1e1e; font-weight:700; font-size:1.15rem; 
                              margin:0 0 1rem; border-bottom:2px solid #8b1e1e; 
                              padding-bottom:0.5rem;">
                        {api_name}: {api_desc}
                    </h4>
                    {formatted_html}
                </div>
                """,
                unsafe_allow_html=True,
            )
    
    employee_id = get_employee_id()
    
    if not st.session_state.get('volatility_feedback_submitted', False):
        fb_choice = st.radio(
            "Select your feedback type:",
            options=[
                "I have read it, found it useful, thanks.",
                "I have read it, found some analyses to be off.",
                "The widget seems interesting, but I have some suggestions on the features.",
            ],
            index=None,
            key="volatility_feedback_radio",
        )
        
        if fb_choice == "I have read it, found it useful, thanks.":
            with st.form("volatility_feedback_form_positive", clear_on_submit=True):
                st.markdown(f'**Employee ID:** {employee_id}')
                if st.form_submit_button("Submit Positive Feedback"):
                    submit_feedback(fb_choice, employee_id=employee_id)
                    st.rerun()
        
        elif fb_choice == "I have read it, found some analyses to be off.":
            with st.form("volatility_feedback_form_analyses", clear_on_submit=True):
                st.markdown("**Please select which volatility analyses seem off:**")
                st.markdown(f'**Employee ID:** {employee_id}')
                selected_issues = {}
                for api_name in st.session_state.volatile_outputs.keys():
                    api_desc = next((cfg["description"] for cfg in API_CONFIGS if cfg["name"] == api_name), api_name)
                    selected = st.checkbox(f"**{api_name}** - {api_desc}", key=f"volatility_issue_{api_name}")
                    if selected:
                        selected_issues[api_name] = True
                additional_feedback = st.text_input("Additional comments:", key="volatility_analyses_additional")
                if st.form_submit_button("Submit Feedback"):
                    if not selected_issues:
                        st.warning("Please select at least one analysis.")
                    else:
                        issues_list = list(selected_issues.keys())
                        off_defs_text = " | ".join(issues_list)
                        submit_feedback(fb_choice, employee_id=employee_id, off_definitions=off_defs_text, additional_feedback=additional_feedback)
                        st.rerun()
        
        elif fb_choice == "The widget seems interesting, but I have some suggestions on the features.":
            with st.form("volatility_feedback_form_suggestions", clear_on_submit=True):
                st.markdown("**Please share your suggestions:**")
                st.markdown(f'**Employee ID:** {employee_id}')
                suggestions = st.text_input("Your suggestions:", key="volatility_suggestions_text")
                if st.form_submit_button("Submit Feedback"):
                    if suggestions.strip():
                        submit_feedback(fb_choice, employee_id=employee_id, suggestions=suggestions)
                        st.rerun()
                    else:
                        st.warning("Please provide your suggestions.")
    
    else:
        st.markdown('<div class="feedback-success">Thank you! Your feedback has been recorded.</div>', unsafe_allow_html=True)
        if st.button("Submit Additional Feedback", key="volatility_reopen_feedback_btn", use_container_width=True):
            st.session_state.volatility_feedback_submitted = False
            st.rerun()

    if st.session_state.get('volatility_feedback_submitted', False):
        st.markdown("---")
        st.markdown(
            """
            <div style="margin: 10px 0;">
                <div class="section-title-box" style="padding: 0.5rem 1rem;">
                    <div style="display:flex; flex-direction:column; align-items:center; justify-content:center;">
                        <h3 style="margin:0; color:white; font-weight:700; font-size:1.2rem;">Download Volatility Analysis</h3>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        combined_output = ""
        for api_name, api_output in st.session_state.volatile_outputs.items():
            if api_output and not api_output.startswith("API Error") and not api_output.startswith("Error:"):
                api_desc = next((cfg["description"] for cfg in API_CONFIGS if cfg["name"] == api_name), api_name)
                combined_output += f"=== {api_name}: {api_desc} ===\n{api_output}\n\n"
        
        if combined_output:
            ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"volatility_analysis_{display_account.replace(' ', '_')}_{ts}.txt"
            download_content = f"""Volatility Analysis Export

Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Company: {display_account}
Industry: {display_industry}
Problem: {problem}

{combined_output}

---
Generated by Volatility Analysis Tool
"""
            st.download_button(
                "Download Volatility Analysis as Text File",
                data=download_content,
                file_name=filename,
                mime="text/plain",
                use_container_width=True
            )
        else:
            st.info("No analysis available for download.")

# =========================================
# BACK BUTTON
# =========================================
st.markdown("---")
if st.button("Back to Main Page", use_container_width=True):
    st.switch_page("Welcome_Agent.py")