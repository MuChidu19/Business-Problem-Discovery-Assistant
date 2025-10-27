def call_api(agent_name, problem, outputs):
    """
    Centralized API call for all agents.
    - agent_name: string, matches the 'name' in API_CONFIGS
    - problem: business problem statement
    - outputs: dict, previous agent outputs (e.g., {'vocabulary': ..., 'current_system': ...})
    """
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
    get_shared_data,
    render_unified_business_inputs,
    render_unified_admin_panel
)
# --- Render Header ---
render_header(
    agent_name="Ambiguity Agent",
    agent_subtitle="Analyzing ambiguity and uncertainty factors in your business problem."
)

# ===============================
# API Configuration for Ambiguity
# ===============================

# Constants
TENANT_ID = "talos"
HEADERS_BASE = {"Content-Type": "application/json"}

# Ambiguity APIs (replace with your actual API URLs)
API_CONFIGS = [
    {
        "name": "Q4",
        "url": "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?society_id=1757657318406&agency_id=1758614809984&level=1",
        "multiround_convo": 2,
        "description": "To what extent do stakeholders share a common understanding of the key terms and concepts?",
        "prompt": lambda problem, outputs: (
            f"Problem statement - {problem}\n\nContext from Vocabulary:\n{outputs.get('vocabulary','')}\n\n"
            f"Context from Current System:\n{outputs.get('current_system','')}\n\n"
            "To what extent do stakeholders share a common understanding and goals about the problem? Score 0–5. Provide justification."
        )
    },
    {
        "name": "Q5",
        "url": "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?society_id=1757657318406&agency_id=1758615038050&level=1",
        "multiround_convo": 2,
        "description": "Are there any conflicting definitions or interpretations that could create confusion",
        "prompt": lambda problem, outputs: (
            f"Problem statement - {problem}\n\nContext from Vocabulary:\n{outputs.get('vocabulary','')}\n\n"
            f"Context from Current System:\n{outputs.get('current_system','')}\n\n"
            "Are there significant conflicts or tradeoffs between stakeholders or system elements? Score 0–5. Provide justification."
        )
    },
    {
        "name": "Q6",
        "url": "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?society_id=1757657318406&agency_id=1758615386880&level=1",
        "multiround_convo": 2,
        "description": "Are objectives, priorities, and constraints clearly communicated and well-defined?",
        "prompt": lambda problem, outputs: (
            f"Problem statement - {problem}\n\nContext from Vocabulary:\n{outputs.get('vocabulary','')}\n\n"
            f"Context from Current System:\n{outputs.get('current_system','')}\n\n"
            "How clear is the problem definition and scope? Score 0–5. Provide justification."
        )
    }
]

# Global feedback file path
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
FEEDBACK_FILE = os.path.join(BASE_DIR, "feedback.csv")

# Initialize feedback file if not present
try:
    if not os.path.exists(FEEDBACK_FILE):
        df = pd.DataFrame(columns=["Timestamp", "Name", "Email", "Feedback", "FeedbackType",
                          "OffDefinitions", "Suggestions", "Account", "Industry", "ProblemStatement"])
        df.to_csv(FEEDBACK_FILE, index=False)
except (PermissionError, OSError) as e:
    if 'feedback_data' not in st.session_state:
        st.session_state.feedback_data = pd.DataFrame(
            columns=["Timestamp", "Name", "Email", "Feedback", "FeedbackType", "OffDefinitions", "Suggestions", "Account", "Industry", "ProblemStatement"])

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
# Utility Functions
# ===============================

def json_to_text(data):
    """Extract text from JSON response"""
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
        # Try to extract any string values
        for value in data.values():
            if isinstance(value, str) and len(value) > 10:
                return value
        return "\n".join(f"{k}: {json_to_text(v)}" for k, v in data.items() if v)
    if isinstance(data, list):
        return "\n".join(json_to_text(x) for x in data if x)
    return str(data)

def sanitize_text(text):
    """Remove markdown artifacts and clean up text"""
    if not text:
        return ""

    # Fix the "s" character issue
    text = re.sub(r'^\s*s\s+', '', text.strip())
    text = re.sub(r'\n\s*s\s+', '\n', text)

    text = re.sub(r'Q\d+\s*Answer\s*Explanation\s*:',
                  '', text, flags=re.IGNORECASE)
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

def format_ambiguity_with_bold(text, extra_phrases=None):
    """Format ambiguity text with bold styling and remove Q1/Answer labels"""
    if not text:
        return "No ambiguity data available"

    clean_text = sanitize_text(text)
    
    # Remove Q1/Answer labels and prefixes
    clean_text = re.sub(r'^\s*Q\d+\s*:', '', clean_text, flags=re.IGNORECASE | re.MULTILINE)
    clean_text = re.sub(r'^\s*Answer\s*:', '', clean_text, flags=re.IGNORECASE | re.MULTILINE)
    clean_text = re.sub(r'^\s*Question\s*\d+\s*:', '', clean_text, flags=re.IGNORECASE | re.MULTILINE)
    clean_text = re.sub(r'\bQ\d+\b\s*:', '', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'\bAnswer\b\s*:', '', clean_text, flags=re.IGNORECASE)
    
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

        # Skip any lines that are just Q1/Answer labels
        if re.match(r'^\s*(Q\d+|Answer|Question\s*\d+)\s*$', ln, re.IGNORECASE):
            i += 1
            continue

        if extra_patterns:
            new_ln = ln
            for pat in extra_patterns:
                try:
                    new_ln = re.sub(
                        pat, lambda m: f"<strong>{m.group(0)}</strong>", new_ln, flags=re.IGNORECASE)
                except re.error:
                    new_ln = re.sub(re.escape(
                        pat), lambda m: f"<strong>{m.group(0)}</strong>", new_ln, flags=re.IGNORECASE)
            if new_ln != ln:
                paragraph_html.append(new_ln)
                i += 1
                continue

        # Section headers (but not Q1/Answer)
        if re.match(r'^\s*(Analysis|Score|Justification|Key\s+Takeaway|Clarity|Definition|Boundaries|Success|Criteria|Requirements|Constraints|Interpretation|Stakeholder|Expectations|Decision|Processes)', ln, flags=re.IGNORECASE):
            paragraph_html.append(f"<strong>{ln.strip()}</strong>")
            i += 1
            continue

        m_num_colon = re.match(r'^\s*(\d+\.\s+[^:]+):\s*(.*)$', ln)
        if m_num_colon:
            heading = m_num_colon.group(1).strip()
            remainder = m_num_colon.group(2).strip()
            paragraph_html.append(
                f"<strong>{heading}:</strong> {remainder}" if remainder else f"<strong>{heading}:</strong>")
            i += 1
            continue

        m_bullet_heading = re.match(r'^\s*(?:•|\d+\.)\s*([^:]+):\s*(.*)$', ln)
        if m_bullet_heading:
            heading = m_bullet_heading.group(1).strip()
            remainder = m_bullet_heading.group(2).strip()
            paragraph_html.append(
                f"• <strong>{heading}:</strong> {remainder}" if remainder else f"• <strong>{heading}:</strong>")
            i += 1
            continue

        m_side = re.match(r'^\s*([^:]+):\s*(.*)$', ln)
        if m_side and len(m_side.group(1).split()) <= 8:
            left = m_side.group(1).strip()
            right = m_side.group(2).strip()
            paragraph_html.append(
                f"<strong>{left}:</strong> {right}" if right else f"<strong>{left}:</strong>")
            i += 1
            continue

        paragraph_html.append(ln)
        i += 1

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

    formatted_output = f"""
    <div class="ambiguity-display">
        {final_html}
    </div>
    """
    formatted_output = re.sub(r'(<br>\s*){3,}', '<br><br>', formatted_output)
    return formatted_output

def submit_feedback(feedback_type, name="", email="", off_definitions="", suggestions="", additional_feedback=""):
    """Submit feedback to CSV file and admin session storage"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Get context data from session state
    account = st.session_state.get("current_account", "")
    industry = st.session_state.get("current_industry", "")
    problem_statement = st.session_state.get("current_problem", "")

    # Create feedback data for admin session
    feedback_data = {
        "Name": name,
        "Email": email, 
        "Feedback": additional_feedback,
        "FeedbackType": feedback_type,
        "OffDefinitions": off_definitions,
        "Suggestions": suggestions,
        "Account": account,
        "Industry": industry,
        "ProblemStatement": problem_statement
    }

    # Save to admin session storage
    save_feedback_to_admin_session(feedback_data, "Ambiguity Agent")

    # Also save to CSV file (original functionality)
    new_entry = pd.DataFrame([[
        timestamp, name, email, additional_feedback, feedback_type, off_definitions, suggestions, account, industry, problem_statement
    ]], columns=["Timestamp", "Name", "Email", "Feedback", "FeedbackType", "OffDefinitions", "Suggestions", "Account", "Industry", "ProblemStatement"])

    try:
        # Try file-based storage first
        if os.path.exists(FEEDBACK_FILE):
            existing = pd.read_csv(FEEDBACK_FILE)

            # Handle schema mismatch
            missing_cols = set(new_entry.columns) - set(existing.columns)
            for col in missing_cols:
                existing[col] = ''

            # Reorder existing columns to match the new entry's order
            existing = existing[new_entry.columns]

            updated = pd.concat([existing, new_entry], ignore_index=True)
        else:
            updated = new_entry

        try:
            updated.to_csv(FEEDBACK_FILE, index=False)
        except (PermissionError, OSError):
            # Fallback to session state on Streamlit Cloud
            if 'feedback_data' not in st.session_state:
                st.session_state.feedback_data = pd.DataFrame(
                    columns=new_entry.columns)
            st.session_state.feedback_data = pd.concat(
                [st.session_state.feedback_data, new_entry], ignore_index=True)
            st.info("📝 Feedback saved to session (cloud mode)")

        # SET AGENT-SPECIFIC FEEDBACK FLAG
        st.session_state.ambiguity_feedback_submitted = True
        return True
    except Exception as e:
        st.error(f"Error saving feedback: {str(e)}")
        return False

def reset_app_state():
    """Completely reset session state to initial values"""
    # Clear ambiguity-related state
    keys_to_clear = ['ambiguity_outputs', 'show_ambiguity', 'feedback_submitted',
                     'feedback_option', 'analysis_complete', 'validation_attempted', 'ambiguity_feedback_submitted']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

    st.success("✅ Application reset successfully! You can start a new analysis.")

# ===============================
# Main Content
# ===============================

# Retrieve data from shared header
shared = get_shared_data()
account = shared.get("account") or ""
industry = shared.get("industry") or ""
problem = shared.get("problem") or ""

# Store current context in session state
st.session_state.current_account = account
st.session_state.current_industry = industry
st.session_state.current_problem = problem

# Retrieve vocab_output and current_system_output from session state
vocab_output = st.session_state.get('vocab_output', '')
current_system_output = st.session_state.get('current_system_data', '')

# Normalize display values
def _norm_display(val, fallback):
    if not val or val in ("Select Account", "Select Industry", "Select Problem"):
        return fallback
    return val

display_account = _norm_display(account, "Unknown Company")
display_industry = _norm_display(industry, "Unknown Industry")

# Use the unified inputs (Welcome-style) so Ambiguity page matches all others
account, industry, problem = render_unified_business_inputs(
    page_key_prefix="ambiguity",
    show_titles=True,
    title_account_industry="Account & Industry",
    title_problem="Business Problem Description",
    save_button_label="✅ Save Problem Details",
)

st.markdown("---")

# ===============================
# Ambiguity Analysis Section
# ===============================

# Validation checks (without warnings)
has_account = account and account != "Select Account"
has_industry = industry and industry != "Select Industry"
has_problem = bool(problem.strip())

# Analyze Ambiguity Button
analyze_btn = st.button("🔍 Analyze Ambiguity", type="primary", use_container_width=True,
                        disabled=not (has_account and has_industry and has_problem))

if analyze_btn:
    # Set validation attempted flag
    st.session_state.validation_attempted = True

    # Final validation before processing
    if not has_account:
        st.error("❌ Please select an account before proceeding.")
        st.stop()

    if not has_industry:
        st.error("❌ Please select an industry before proceeding.")
        st.stop()

    if not has_problem:
        st.error("❌ Please enter a business problem description.")
        st.stop()

    # Build context
    full_context = f"""
    Business Problem:
    {problem.strip()}

    Context:
    Account: {account}
    Industry: {industry}
    """.strip()

    # Prepare headers with authentication
    headers = HEADERS_BASE.copy()
    headers.update({
        "Tenant-ID": TENANT_ID,
        "X-Tenant-ID": TENANT_ID
    })

    if st.session_state.auth_token:
        headers["Authorization"] = f"Bearer {st.session_state.auth_token}"

    with st.spinner("🔍 Analyzing ambiguity"):
        progress = st.progress(0)
        st.session_state.ambiguity_outputs = {}

        try:
            with requests.Session() as session:
                total_apis = len(API_CONFIGS)
                
                for i, api_cfg in enumerate(API_CONFIGS):
                    progress.progress(i / total_apis)
                    
                    try:
                        goal = api_cfg["prompt"](full_context, {})
                        
                        # Make API request with timeout
                        response = session.post(
                            api_cfg["url"],
                            headers=headers,
                            json={"agency_goal": goal},
                            timeout=60
                        )

                        if response.status_code == 200:
                            # Process successful response
                            result_data = response.json()
                            text_output = json_to_text(result_data)
                            cleaned_text = sanitize_text(text_output)
                            
                            st.session_state.ambiguity_outputs[api_cfg["name"]] = cleaned_text
                        else:
                            error_msg = f"API Error {response.status_code}: {response.text[:200]}"
                            st.session_state.ambiguity_outputs[api_cfg["name"]] = error_msg

                    except requests.exceptions.Timeout:
                        st.session_state.ambiguity_outputs[api_cfg["name"]] = "Request timeout: The API took too long to respond."
                    except Exception as e:
                        st.session_state.ambiguity_outputs[api_cfg["name"]] = f"Error: {str(e)}"

                progress.progress(1.0)
                st.session_state.show_ambiguity = True
                st.session_state.analysis_complete = True
                st.success("✅ Ambiguity analysis complete!")

        except Exception as e:
            st.error(f"An unexpected error occurred during analysis: {str(e)}")

# ===============================
# Display Ambiguity Results
# ===============================

def clean_ambiguity_output(text):
    """Clean ambiguity output by removing Q1/Q2/Q3 prefixes, HTML tags, and fixing formatting"""
    if not text:
        return "No ambiguity data available"

    clean_text = re.sub(r'<[^>]+>', '', text)
    clean_text = re.sub(r'^(Q\d+\.?\s*)', '', clean_text, flags=re.MULTILINE | re.IGNORECASE)
    clean_text = re.sub(r'\n(Q\d+\.?\s*)', '\n', clean_text, flags=re.MULTILINE | re.IGNORECASE)
    clean_text = re.sub(r'^(Question\s*\d+\.?\s*)', '', clean_text, flags=re.MULTILINE | re.IGNORECASE)
    clean_text = re.sub(r'\n(Question\s*\d+\.?\s*)', '\n', clean_text, flags=re.MULTILINE | re.IGNORECASE)
    clean_text = re.sub(r'^(Answer|Analysis)\s*:\s*', '', clean_text, flags=re.MULTILINE | re.IGNORECASE)
    clean_text = re.sub(r'Score\s*\(0[-–]5\)\s*:', 'Score:', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'^\s+', '', clean_text, flags=re.MULTILINE)
    clean_text = re.sub(r'\n\s+', '\n', clean_text)
    clean_text = re.sub(r' {2,}', ' ', clean_text)
    clean_text = re.sub(r'\n{3,}', '\n\n', clean_text)
    return clean_text.strip()


if st.session_state.get("show_ambiguity") and st.session_state.get("ambiguity_outputs"):
    st.markdown("---")

    display_account = globals().get("display_account") or st.session_state.get("saved_account", "Unknown Company")
    display_industry = globals().get("display_industry") or st.session_state.get("saved_industry", "Unknown Industry")

    # Section header - Updated to match Vocabulary style
    st.markdown(
        f"""
        <div style="margin: 20px 0;">
            <div class="section-title-box" style="padding: 1rem 1.5rem;">
                <div style="display:flex; flex-direction:column; align-items:center; justify-content:center;">
                    <h3 style="margin-bottom:8px; color:white; font-weight:800; font-size:1.4rem; line-height:1.2;">
                        Ambiguity Analysis
                    </h3>
                    <p style="font-size:0.95rem; color:white; margin:0; line-height:1.5; text-align:center; max-width: 800px;">
                        Please note that it is an <strong>AI-generated Ambiguity Analysis</strong>, derived from 
                        the <em>company</em> <strong>{display_account}</strong> and 
                        the <em>industry</em> <strong>{display_industry}</strong> based on the 
                        <em>problem statement</em> you shared.<br>
                        In case you find something off, there's a provision to share feedback at the bottom 
                        we encourage you to use it.
                    </p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Loop through ambiguity results
    for i, (api_name, api_output) in enumerate(st.session_state["ambiguity_outputs"].items()):
        question_description = ""
        for cfg in API_CONFIGS:
            if cfg.get("name") == api_name:
                question_description = cfg.get("description", "")
                break

        clean_question = re.sub(r'^Q\d+\.?\s*', '', question_description or "").strip() or api_name.replace("_", " ").title()
        cleaned_output = clean_ambiguity_output(api_output)

        # Replace company/industry names
        if display_account and display_account != "Unknown Company":
            cleaned_output = re.sub(r'\bthe company\b', display_account, cleaned_output, flags=re.IGNORECASE)
        if display_industry and display_industry != "Unknown Industry":
            cleaned_output = re.sub(r'\bthe industry\b', display_industry, cleaned_output, flags=re.IGNORECASE)

        # Format output with proper list formatting + bold labels + left alignment
        formatted_output = cleaned_output

        # Convert numbered and dash lists to bullets
        formatted_output = re.sub(r'(?m)^\s*(?:\d+\.|-)\s+(.*)', r'• \1', formatted_output)

        # Ensure bullets always start on a new line (even if inline after colon)
        formatted_output = re.sub(r':\s*•', ':\n•', formatted_output)

        # Handle sentences ending with ":" followed by bullet text
        formatted_output = re.sub(r'(:)\s+(?=•)', r'\1\n', formatted_output)

        # Add newline before bullets (to separate from paragraphs)
        formatted_output = re.sub(r'(?<!\n)\s*•', r'\n•', formatted_output)

        # Bold text before colon, including bullets
        formatted_output = re.sub(
            r'(^|[\n])\s*(•\s*)?([^:\n]{2,80}):',
            lambda m: f"{m.group(1)}{m.group(2) or ''}<strong>{m.group(3).strip()}:</strong>",
            formatted_output
        )

        # Remove extra blank lines
        formatted_output = re.sub(r'\n{2,}', '\n', formatted_output)

        # Convert newlines to <br>
        html_body = formatted_output.replace('\n', '<br>')

        # Content box with red border styling like Vocabulary
        st.markdown(
            f"""
            <div style="
                background: var(--bg-card);
                border: 2px solid #8b1e1e;
                border-radius: 16px;
                padding: 1.6rem;
                margin-bottom: 1.6rem;
                box-shadow: 0 3px 10px rgba(139,30,30,0.15);
            ">
                <h4 style="
                    color: #8b1e1e;
                    font-weight: 700;
                    font-size: 1.15rem;
                    margin: 0 0 1rem 0;
                    border-bottom: 2px solid #8b1e1e;
                    padding-bottom: 0.5rem;
                    text-align: left;
                ">
                    {clean_question}
                </h4>
                <div style="
                    color: var(--text-primary);
                    line-height: 1.45;
                    font-size: 1rem;
                    text-align: left;
                    white-space: normal;
                ">
                    {html_body}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # ===============================
    # User Feedback Section (Only show after extraction)
    # ===============================

    st.markdown("---")
    st.markdown('<div class="section-title-box" style="text-align:center;"><h3>💬 User Feedback</h3></div>',
                unsafe_allow_html=True)
    
    # UPDATED MESSAGE - Agent-specific
    st.markdown("Please share your thoughts or suggestions after reviewing the **ambiguity analysis**.")

    # Get employee ID from login page
    def get_user_id():
        if 'employee_id' in st.session_state and st.session_state.employee_id:
            return st.session_state.employee_id
        
        possible_keys = ['user_id', 'userID', 'user', 'username', 'employee_id', 'EmployeeID']
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

    # Get the actual user ID
    user_id = get_user_id()

    # Updated submit_feedback function call
    def submit_feedback_wrapper(feedback_type, user_id="", off_definitions="", suggestions="", additional_feedback=""):
        """Wrapper for submit_feedback to handle employee ID"""
        return submit_feedback(
            feedback_type=feedback_type,
            name=user_id,  # Map user_id to name parameter
            off_definitions=off_definitions,
            suggestions=suggestions,
            additional_feedback=additional_feedback
        )

    # Show feedback section if not submitted - USING AGENT-SPECIFIC FLAG
    if not st.session_state.get('ambiguity_feedback_submitted', False):
        fb_choice = st.radio(
            "Select your feedback type:",
            options=[
                "I have read it, found it useful, thanks.",
                "I have read it, found some analyses to be off.",
                "The widget seems interesting, but I have some suggestions on the features.",
            ],
            index=None,
            key="ambiguity_feedback_radio",  # Agent-specific key
        )

        if fb_choice:
            st.session_state.feedback_option = fb_choice

        # Feedback form 1: Positive feedback - SIMPLIFIED
        if fb_choice == "I have read it, found it useful, thanks.":
            with st.form("ambiguity_feedback_form_positive", clear_on_submit=True):
                st.info("Thank you for your positive feedback!")
                # ONLY EMPLOYEE ID - NO OTHER FIELDS
                st.markdown(f'**Employee ID:** {user_id}')
                
                submitted = st.form_submit_button("📨 Submit Positive Feedback", type="primary")
                if submitted:
                    if submit_feedback_wrapper(fb_choice, user_id=user_id):
                        st.session_state.ambiguity_feedback_submitted = True
                        st.success("✅ Thank you! Your feedback has been recorded.")
                        st.rerun()

        # Feedback form 2: Analyses off - SIMPLIFIED
        elif fb_choice == "I have read it, found some analyses to be off.":
            with st.form("ambiguity_feedback_form_analyses", clear_on_submit=True):
                st.markdown("**Please select which ambiguity analyses seem off:**")
                
                # ONLY EMPLOYEE ID - NO OTHER FIELDS
                st.markdown(f'**Employee ID:** {user_id}')

                # Show checkboxes for each ambiguity question
                st.markdown("### Select problematic analyses:")
                selected_issues = {}
                
                for api_name in st.session_state.ambiguity_outputs.keys():
                    selected = st.checkbox(
                        f"**{api_name}** - {API_CONFIGS[next(i for i, cfg in enumerate(API_CONFIGS) if cfg['name'] == api_name)]['description']}",
                        key=f"ambiguity_issue_{api_name}",
                        help=f"Select if {api_name} analysis seems incorrect"
                    )
                    if selected:
                        selected_issues[api_name] = True

                additional_feedback = st.text_input(
                    "Additional comments:",
                    placeholder="Please provide more details about the analysis issues you found...",
                    key="ambiguity_analyses_additional"
                )

                submitted = st.form_submit_button("📨 Submit Feedback", type="primary")
                if submitted:
                    if not selected_issues:
                        st.warning("⚠️ Please select at least one analysis that seems off.")
                    else:
                        issues_list = list(selected_issues.keys())
                        off_defs_text = " | ".join(issues_list)
                        if submit_feedback_wrapper(fb_choice, user_id=user_id, off_definitions=off_defs_text, additional_feedback=additional_feedback):
                            st.session_state.ambiguity_feedback_submitted = True
                            st.success("✅ Thank you! Your feedback has been recorded.")
                            st.rerun()

        # Feedback form 3: Suggestions - SIMPLIFIED
        elif fb_choice == "The widget seems interesting, but I have some suggestions on the features.":
            with st.form("ambiguity_feedback_form_suggestions", clear_on_submit=True):
                st.markdown("**Please share your suggestions for improvement:**")
                
                # ONLY EMPLOYEE ID - NO OTHER FIELDS
                st.markdown(f'**Employee ID:** {user_id}')
                
                suggestions = st.text_input(
                    "Your suggestions:",
                    placeholder="What features would you like to see improved or added?",
                    key="ambiguity_suggestions_text"
                )
                submitted = st.form_submit_button("📨 Submit Feedback", type="primary")
                if submitted:
                    if not suggestions.strip():
                        st.warning("⚠️ Please provide your suggestions.")
                    else:
                        if submit_feedback_wrapper(fb_choice, user_id=user_id, suggestions=suggestions):
                            st.session_state.ambiguity_feedback_submitted = True
                            st.success("✅ Thank you! Your feedback has been recorded.")
                            st.rerun()
    else:
        # Feedback already submitted - USING AGENT-SPECIFIC FLAG
        st.success("✅ Thank you! Your feedback has been recorded.")
        if st.button("📝 Submit Additional Feedback", key="ambiguity_reopen_feedback_btn", type="primary"):
            st.session_state.ambiguity_feedback_submitted = False
            st.rerun()

    # ===============================
    # Download Section (Only show after feedback submission - AGENT-SPECIFIC)
    # ===============================

    # USING AGENT-SPECIFIC FLAG for download section
    if st.session_state.get('ambiguity_feedback_submitted', False):
        st.markdown("---")
        st.markdown(
            """
            <div style="margin: 10px 0;">
                <div class="section-title-box" style="padding: 0.5rem 1rem;">
                    <div style="display:flex; flex-direction:column; align-items:center; justify-content:center;">
                        <h3 style="margin:0; color:white; font-weight:700; font-size:1.2rem; line-height:1.2;">
                            📥 Download Ambiguity Analysis
                        </h3>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Combine all ambiguity outputs for download
        combined_output = ""
        for api_name, api_output in st.session_state.ambiguity_outputs.items():
            if api_output and not api_output.startswith("API Error") and not api_output.startswith("Error:"):
                combined_output += f"=== {api_name} ===\n{api_output}\n\n"

        if combined_output:
            ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"ambiguity_analysis_{display_account.replace(' ', '_')}_{ts}.txt"
            download_content = f"""Ambiguity Analysis Export
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Company: {display_account}
Industry: {display_industry}

{combined_output}
---
Generated by Ambiguity Analysis Tool
"""
            st.download_button(
                "⬇️ Download Ambiguity Analysis as Text File",
                data=download_content,
                file_name=filename,
                mime="text/plain",
                use_container_width=True
            )
        else:
            st.info(
                "No ambiguity analysis available for download. Please complete the analysis first.")

# =========================================
# ⬅️ BACK BUTTON
# =========================================
st.markdown("---")
if st.button("⬅️ Back to Main Page", use_container_width=True):
    st.switch_page("Welcome_Agent.py")
