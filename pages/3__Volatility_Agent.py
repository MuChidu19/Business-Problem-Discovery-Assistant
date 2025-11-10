# pip install markdown2 requests pandas

import streamlit as st
import streamlit.components.v1 as components
import os
import re
import json
from datetime import datetime
import pandas as pd
import requests
import markdown2

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
# 🧭 PAGE CONFIG
# =========================================
st.set_page_config(
    page_title="Volatility Agent",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================================
# ⚙️ SESSION INITIALIZATION - AGENT-SPECIFIC
# =========================================
session_defaults = {
    'volatile_outputs': {},
    'show_volatility': False,
    'feedback_submitted': False,
    'feedback_option': None,
    'analysis_complete': False,
    'validation_attempted': False,
    # AGENT-SPECIFIC FEEDBACK TRACKING
    'volatility_feedback_submitted': False,  # Unique to this agent
}

for key, val in session_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# =========================================
# 🌐 API CONFIGURATION
# =========================================
TENANT_ID = "talos"
HEADERS_BASE = {"Content-Type": "application/json"}

# Retrieve vocab_output and current_system_output from session state
vocab_output = st.session_state.get('vocab_output', '')
current_system_output = st.session_state.get('current_system_data', '')

# Volatility APIs
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
# 📁 FILE CONFIG
# =========================================
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
FEEDBACK_FILE = os.path.join(BASE_DIR, "feedback.csv")

# Initialize feedback file if not present
try:
    if not os.path.exists(FEEDBACK_FILE):
        df = pd.DataFrame(columns=[
            "Timestamp", "employee_id", "Feedback", "FeedbackType", 
            "OffDefinitions", "Suggestions", "Account", "Industry", "ProblemStatement"
        ])
        df.to_csv(FEEDBACK_FILE, index=False)
except (PermissionError, OSError) as e:
    if 'feedback_data' not in st.session_state:
        st.session_state.feedback_data = pd.DataFrame(
            columns=["Timestamp", "employee_id", "Feedback", "FeedbackType", 
                    "OffDefinitions", "Suggestions", "Account", "Industry", "ProblemStatement"])

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

# =========================================
# 🧹 HELPER FUNCTIONS - ENHANCED WITH BETTER FORMATTING
# =========================================

def json_to_text(data):
    """Extract text from JSON response - same as vocabulary agent"""
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

def markdown_to_html(md_text: str) -> str:
    """Convert markdown text to HTML with formatting - same as vocabulary approach"""
    if not md_text:
        return "<p>No content</p>"
    
    # Clean up stray 's' characters (same as vocab code)
    md_text = re.sub(r'^\s*s\s+', '', md_text.strip())
    md_text = re.sub(r'\n\s*s\s+', '\n', md_text)
    
    # Convert markdown to HTML with extras
    html = markdown2.markdown(
        md_text,
        extras=["fenced-code-blocks", "tables", "break-on-newline", 
                "cuddled-lists", "header-ids", "strike", "task_list"]
    )
    
    # Post-process HTML for better styling (same as vocab approach)
    html = re.sub(
        r"<p>\s*([^<\n]+?)\s*:</p>", 
        lambda m: f"<p><strong>{m.group(1)}</strong>:</p>", 
        html, 
        flags=re.IGNORECASE
    )
    
    # Apply consistent paragraph styling
    html = re.sub(
        r"<p>", 
        r'<p style="margin:6px 0; line-height:1.45; font-size:0.98rem;">', 
        html
    )
    
    return html

def sanitize_text_light(text):
    """Light sanitization preserving important formatting markers"""
    if not text:
        return ""
    
    # Fix the "s" character issue
    text = re.sub(r'^\s*s\s+', '', text.strip())
    text = re.sub(r'\n\s*s\s+', '\n', text)
    
    # Clean up excessive whitespace but preserve structure
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    text = re.sub(r' {3,}', '  ', text)
    
    # Clean up some problematic patterns while preserving structure
    text = re.sub(r'Q\d+\s*Answer\s*Explanation\s*:', '', text, flags=re.IGNORECASE)
    text = re.sub(r'& Key Takeaway:', 'Key Takeaway:', text)
    
    return text.strip()

def format_volatility_with_bold(text, extra_phrases=None):
    """ENHANCED Format volatility text with bold styling - BETTER HEADING DETECTION"""
    if not text:
        return "No volatility data available"
    
    # Use light sanitization to preserve formatting markers
    clean_text = sanitize_text_light(text)
    
    # Remove Q1/Answer labels and prefixes but preserve structure
    clean_text = re.sub(r'^\s*Q\d+\s*:\s*', '', clean_text, flags=re.IGNORECASE | re.MULTILINE)
    clean_text = re.sub(r'^\s*Answer\s*:\s*', '', clean_text, flags=re.IGNORECASE | re.MULTILINE)
    clean_text = re.sub(r'^\s*Question\s*\d+\s*:\s*', '', clean_text, flags=re.IGNORECASE | re.MULTILINE)
    clean_text = re.sub(r'\bQ\d+\b\s*:\s*', '', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'\bAnswer\b\s*:\s*', '', clean_text, flags=re.IGNORECASE)
    
    # Convert bullets
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
    
    def is_heading_line(line):
        """Enhanced heading detection"""
        line = line.strip()
        if not line:
            return False
        
        # Check for various heading patterns
        heading_patterns = [
            r'^\*\*(.+?)\*\*$',  # **Bold text**
            r'^#+\s+(.+)$',       # # Markdown headers
            r'^([A-Z][^:]{2,30}):\s*$',  # CAPS WORD:
            r'^(\d+\.\s*[A-Z].{3,50}):\s*$',  # 1. Something:
            r'^(Analysis|Score|Justification|Frequency|Pace|Change|Conclusion|Summary|Key\s+Points?|Important|Critical|Major|Primary|Secondary)(\s|:|\.|$)',
            r'^(Cyclical|Predictable|Sporadic|Unpredictable|Resilient|System|Rework|Disruption|Impact|Effect|Influence)(\s|:|\.|$)',
            r'^(Input\s+Changes?|Business\s+Impact|System\s+Response|Adaptability|Flexibility)(\s|:|\.|$)',
            r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*:?\s*$',  # Title Case words
        ]
        
        for pattern in heading_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                return True
        
        # Check if line is short and looks like a header (but not too short)
        if 3 <= len(line) <= 80 and ':' not in line and not line.startswith('•'):
            # If it's mostly caps or title case
            if re.match(r'^[A-Z][A-Z\s]{2,}$', line) or re.match(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*$', line):
                return True
        
        return False
    
    def collect_continuation(start_idx):
        """Collect continuation lines for block-style headings"""
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
        
        # Skip any remaining Q1/Answer labels
        if re.match(r'^\s*(Q\d+|Answer|Question\s*\d+)\s*$', ln, re.IGNORECASE):
            i += 1
            continue
        
        # Handle extra phrases first
        if extra_patterns:
            new_ln = ln
            for pat in extra_patterns:
                try:
                    new_ln = re.sub(
                        pat, lambda m: f"<strong>{m.group(0)}</strong>",
                        new_ln, flags=re.IGNORECASE)
                except re.error:
                    new_ln = re.sub(re.escape(
                        pat), lambda m: f"<strong>{m.group(0)}</strong>",
                        new_ln, flags=re.IGNORECASE)
            if new_ln != ln:
                paragraph_html.append(new_ln)
                i += 1
                continue
        
        # ENHANCED: Check if this line is a heading
        if is_heading_line(ln):
            # Clean up markdown formatting if present
            cleaned_heading = re.sub(r'^\*\*(.*?)\*\*$', r'\1', ln.strip())
            cleaned_heading = re.sub(r'^#+\s+', '', cleaned_heading)
            paragraph_html.append(f"<strong style='color: var(--text-primary); font-size:1.05rem;'>{cleaned_heading}</strong>")
            i += 1
            continue
        
        # Numbered heading WITH colon - ENHANCED
        m_num_colon = re.match(r'^\s*(\d+\.\s*[^:]+):\s*(.*)$', ln)
        if m_num_colon:
            heading = m_num_colon.group(1).strip()
            remainder = m_num_colon.group(2).strip()
            if remainder:
                paragraph_html.append(
                    f"<strong style='color: var(--text-primary);'>{heading}:</strong> {remainder}")
            else:
                paragraph_html.append(f"<strong style='color: var(--text-primary);'>{heading}:</strong>")
            i += 1
            continue
        
        # Numbered heading WITHOUT colon - ENHANCED
        m_num_no_colon = re.match(r'^\s*(\d+\.\s*.+)$', ln)
        if m_num_no_colon and len(ln.strip()) <= 80:  # Reasonable heading length
            block, j = collect_continuation(i)
            block_text = "<br>".join([b.strip() for b in block])
            paragraph_html.append(f"<strong style='color: var(--text-primary);'>{block_text}</strong>")
            i = j
            continue
        
        # Bullet with colon - ENHANCED
        m_bullet_heading = re.match(r'^\s*(?:•|\d+\.)\s*([^:]+):\s*(.*)$', ln)
        if m_bullet_heading:
            heading = m_bullet_heading.group(1).strip()
            remainder = m_bullet_heading.group(2).strip()
            if remainder:
                paragraph_html.append(
                    f"• <strong style='color: var(--text-primary);'>{heading}:</strong> {remainder}")
            else:
                paragraph_html.append(f"• <strong style='color: var(--text-primary);'>{heading}:</strong>")
            i += 1
            continue
        
        # Generic inline heading "LeftOfColon: rest" - MUCH MORE FLEXIBLE
        m_side = re.match(r'^\s*([^:]+):\s*(.*)$', ln)
        if m_side and 3 <= len(m_side.group(1).split()) <= 15:  # More flexible word count
            left = m_side.group(1).strip()
            right = m_side.group(2).strip()
            # Check if left part looks like a heading (not a sentence)
            if not re.search(r'\b(is|are|was|were|has|have|will|would|can|could|the|a|an)\b', left, re.IGNORECASE):
                paragraph_html.append(
                    f"<strong style='color: var(--text-primary);'>{left}:</strong> {right}" if right 
                    else f"<strong style='color: var(--text-primary);'>{left}:</strong>")
                i += 1
                continue
        
        # Handle lines that end with colon (potential headings)
        if ln.strip().endswith(':') and 3 <= len(ln.strip()) <= 60:
            heading = ln.strip()[:-1]  # Remove the colon
            if not re.search(r'\b(is|are|was|were|has|have|will|would|can|could)\b', heading, re.IGNORECASE):
                paragraph_html.append(f"<strong style='color: var(--text-primary);'>{heading}:</strong>")
                i += 1
                continue
        
        # Default case - regular text
        paragraph_html.append(f"<span style='color: var(--text-primary);'>{ln}</span>")
        i += 1
    
    # Group into paragraphs
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
    
    # Wrap paragraphs with proper styling
    para_wrapped = [
        f"<p style='margin:6px 0; line-height:1.45; font-size:0.98rem; color: var(--text-primary);'>{p}</p>"
        for p in final_paragraphs if p.strip()
    ]
    final_html = "\n".join(para_wrapped)
    
    # Clean up excessive line breaks
    formatted_output = f"""
    <div class="volatility-display">
        {final_html}
    </div>
    """
    formatted_output = re.sub(r'(<br>\s*){3,}', '<br><br>', formatted_output)
    return formatted_output

def call_api(agent_name, problem, outputs):
    """Call the Talos API using centralized API_CONFIGS"""
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
            return sanitize_text_light(json_to_text(response.json()))
        else:
            st.error(f"API Error: {response.status_code} - {response.text[:200]}")
            return None
    except Exception as e:
        st.error(f"API Call Failed: {str(e)}")
        return None

def get_employee_id():
    """Get employee ID from various sources - same as vocabulary agent"""
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
    """Submit feedback to CSV file and admin session storage"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Get context data from session state
    account = st.session_state.get("current_account", "")
    industry = st.session_state.get("current_industry", "")
    problem_statement = st.session_state.get("current_problem", "")
    
    # Column order matching vocabulary agent
    columns = [
        "Timestamp", "Employee_id", "Feedback", "FeedbackType",
        "OffDefinitions", "Suggestions", "Account", "Industry", "ProblemStatement"
    ]
    
    row = [
        timestamp, employee_id, additional_feedback, feedback_type,
        off_definitions, suggestions, account, industry, problem_statement
    ]
    
    entry = pd.DataFrame([row], columns=columns)
    
    # Save to admin session (no timestamp)
    admin_data = {
        "Employee_id": employee_id,
        "Feedback": additional_feedback,
        "FeedbackType": feedback_type,
        "OffDefinitions": off_definitions,
        "Suggestions": suggestions,
        "Account": account,
        "Industry": industry,
        "ProblemStatement": problem_statement
    }
    save_feedback_to_admin_session(admin_data, "Volatility Agent")
    
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
    
    st.session_state.volatility_feedback_submitted = True
    return True

def reset_app_state():
    """Completely reset session state to initial values"""
    keys_to_clear = ['volatile_outputs', 'show_volatility', 'feedback_submitted',
                     'feedback_option', 'analysis_complete', 'validation_attempted',
                     'volatility_feedback_submitted']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    st.success("✅ Application reset successfully! You can start a new analysis.")

# =========================================
# 🧩 UI COMPONENTS
# =========================================
render_header(
    agent_name="Volatility Agent",
    agent_subtitle="Analyzing volatility and variability factors in your business problem.",
    enable_admin_access=True,
    header_height=85
)

# Retrieve data from shared header
shared = get_shared_data()
account = shared.get("account") or ""
industry = shared.get("industry") or ""
problem = shared.get("problem") or ""

# Store current context in session state
st.session_state.current_account = account
st.session_state.current_industry = industry
st.session_state.current_problem = problem

# Normalize display values
def _norm_display(val, fallback):
    if not val or val in ("Select Account", "Select Industry", "Select Problem"):
        return fallback
    return val

display_account = _norm_display(account, "Unknown Company")
display_industry = _norm_display(industry, "Unknown Industry")

# Use the unified inputs (Welcome-style) so Volatility page matches all others
account, industry, problem = render_unified_business_inputs(
    page_key_prefix="volatility",
    show_titles=True,
    title_account_industry="Account & Industry",
    title_problem="Business Problem Description",
    save_button_label="✅ Save Problem Details",
)

st.markdown("---")

# =========================================
# 🚀 VOLATILITY ANALYSIS SECTION
# =========================================
has_account = account and account != "Select Account"
has_industry = industry and industry != "Select Industry"
has_problem = bool(problem.strip())

# Analyze Volatility Button
analyze_btn = st.button(
    "🔍 Analyze Volatility", 
    type="primary", 
    use_container_width=True,
    disabled=not (has_account and has_industry and has_problem)
)

if analyze_btn:
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
    Business Problem: {problem.strip()}
    Context:
    Account: {account}
    Industry: {industry}
    """.strip()
    
    with st.spinner("🔍 Analyzing volatility and variability factors..."):
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
        st.success("✅ Volatility analysis complete!")

# =========================================
# 📊 DISPLAY VOLATILITY RESULTS
# =========================================
if st.session_state.get("show_volatility") and st.session_state.get("volatile_outputs"):
    st.markdown("---")
    
    # Header - same style as vocabulary agent
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
    
    # Display each volatility analysis with ENHANCED formatting
    for api_name, api_output in st.session_state.volatile_outputs.items():
        if api_output and api_output != "No data available":
            # Get API description
            api_desc = next((cfg["description"] for cfg in API_CONFIGS if cfg["name"] == api_name), api_name)
            
            # Use ENHANCED formatting function
            formatted_html = format_volatility_with_bold(api_output)
            
            # Apply company/industry replacements (same as vocab approach)
            if display_account != "Unknown Company":
                formatted_html = re.sub(
                    r'\bthe company\b', 
                    display_account, 
                    formatted_html, 
                    flags=re.IGNORECASE
                )
            
            if display_industry != "Unknown Industry":
                formatted_html = re.sub(
                    r'\bthe industry\b', 
                    display_industry, 
                    formatted_html, 
                    flags=re.IGNORECASE
                )
            
            # Display with same styling as vocabulary agent
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
                """,
                unsafe_allow_html=True,
            )
    
    # Get employee ID
    employee_id = get_employee_id()
    
    # Feedback section - same pattern as vocabulary agent
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
                st.info("Thank you for your positive feedback!")
                st.markdown(f'**Employee ID:** {employee_id}')
                
                if st.form_submit_button("Submit Positive Feedback"):
                    submit_feedback(fb_choice, employee_id=employee_id)
                    st.rerun()
        
        elif fb_choice == "I have read it, found some analyses to be off.":
            with st.form("volatility_feedback_form_analyses", clear_on_submit=True):
                st.markdown("**Please select which volatility analyses seem off:**")
                st.markdown(f'**Employee ID:** {employee_id}')
                
                st.markdown("### Select problematic analyses:")
                selected_issues = {}
                for api_name in st.session_state.volatile_outputs.keys():
                    api_desc = next((cfg["description"] for cfg in API_CONFIGS if cfg["name"] == api_name), api_name)
                    selected = st.checkbox(
                        f"**{api_name}** - {api_desc}",
                        key=f"volatility_issue_{api_name}",
                        help=f"Select if {api_name} analysis seems incorrect"
                    )
                    if selected:
                        selected_issues[api_name] = True
                
                additional_feedback = st.text_input(
                    "Additional comments:",
                    placeholder="Please provide more details about the analysis issues you found...",
                    key="volatility_analyses_additional"
                )
                
                if st.form_submit_button("Submit Feedback"):
                    if not selected_issues:
                        st.warning("⚠️ Please select at least one analysis that seems off.")
                    else:
                        issues_list = list(selected_issues.keys())
                        off_defs_text = " | ".join(issues_list)
                        submit_feedback(
                            fb_choice,
                            employee_id=employee_id,
                            off_definitions=off_defs_text,
                            additional_feedback=additional_feedback
                        )
                        st.rerun()
        
        elif fb_choice == "The widget seems interesting, but I have some suggestions on the features.":
            with st.form("volatility_feedback_form_suggestions", clear_on_submit=True):
                st.markdown("**Please share your suggestions for improvement:**")
                st.markdown(f'**Employee ID:** {employee_id}')
                
                suggestions = st.text_input(
                    "Your suggestions:",
                    placeholder="What features would you like to see improved or added?",
                    key="volatility_suggestions_text"
                )
                
                if st.form_submit_button("Submit Feedback"):
                    if suggestions.strip():
                        submit_feedback(fb_choice, employee_id=employee_id, suggestions=suggestions)
                        st.rerun()
                    else:
                        st.warning("⚠️ Please provide your suggestions.")
    
    else:
        st.markdown('<div class="feedback-success">Thank you! Your feedback has been recorded.</div>', unsafe_allow_html=True)
        if st.button("Submit Additional Feedback", key="volatility_reopen_feedback_btn", use_container_width=True):
            st.session_state.volatility_feedback_submitted = False
            st.rerun()

    # Download Section (Only show after feedback submission)
    if st.session_state.get('volatility_feedback_submitted', False):
        st.markdown("---")
        st.markdown(
            """
            <div style="margin: 10px 0;">
                <div class="section-title-box" style="padding: 0.5rem 1rem;">
                    <div style="display:flex; flex-direction:column; align-items:center; justify-content:center;">
                        <h3 style="margin:0; color:white; font-weight:700; font-size:1.2rem; line-height:1.2;">
                            📥 Download Volatility Analysis
                        </h3>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        # Combine all volatility outputs for download
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
                "⬇️ Download Volatility Analysis as Text File",
                data=download_content,
                file_name=filename,
                mime="text/plain",
                use_container_width=True
            )
        else:
            st.info("No volatility analysis available for download. Please complete the analysis first.")

# =========================================
# ⬅️ BACK BUTTON
# =========================================
st.markdown("---")
if st.button("⬅️ Back to Main Page", use_container_width=True):
    st.switch_page("Welcome_Agent.py")
