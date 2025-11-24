from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import requests

from app.models import AnalyzeRequest, AnalyzeResponse, Feedback
from app.services.feedback import append_feedback, read_feedback
from app.services.talos import call_talos
from app.utils.text import format_compact_output
from app.utils.account_industry import ACCOUNTS, INDUSTRIES, ACCOUNT_INDUSTRY_MAP


app = FastAPI(title="Business Problem Discovery Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
FEEDBACK_FILE = os.path.join(DATA_DIR, "feedback.csv")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/constants/accounts")
def get_accounts():
    return {
        "accounts": ACCOUNTS,
        "industries": INDUSTRIES,
        "map": ACCOUNT_INDUSTRY_MAP,
    }


@app.get("/api/admin/feedback")
def get_feedback():
    df = read_feedback(FEEDBACK_FILE)
    return {"rows": df.to_dict(orient="records")}


@app.post("/api/feedback")
def post_feedback(fb: Feedback):
    try:
        append_feedback(FEEDBACK_FILE, fb.model_dump())
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# Agent: Vocabulary
# ================================

VOCAB_URL = (
    "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?"
    "society_id=1757657318406&agency_id=1758548233201&level=1"
)


@app.post("/api/agents/vocabulary/analyze", response_model=AnalyzeResponse)
def analyze_vocabulary(req: AnalyzeRequest):
    if not req.problem or req.account in (None, ""):
        raise HTTPException(status_code=400, detail="Missing required fields: problem, account")

    prompt = f"{req.problem}\n\nExtract the vocabulary from this problem statement."
    try:
        raw_text = call_talos(VOCAB_URL, prompt, multiround_convo=max(1, req.multiround_convo or 1))
        html = format_compact_output(raw_text, body_line_height=1.30)
        return AnalyzeResponse(output_text=html, meta={
            "agent": "vocabulary",
            "account": req.account,
            "industry": req.industry,
        })
    except requests.HTTPError as e:  # type: ignore[name-defined]
        # Keep simple to avoid tight coupling, rethrow as HTTP error
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# Agent: Industry Research
# ================================

INDUSTRY_URL = (
    "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?"
    "society_id=1757657318406&agency_id=1762325261936&level=1"
)


@app.post("/api/agents/industry-research/analyze", response_model=AnalyzeResponse)
def analyze_industry(req: AnalyzeRequest):
    prompt = (
        f"{req.problem}\n\n"
        "Explore and document the industry connected to the above problem statement.\n"
        "Cover operations, market structure, customers, competitive landscape, supply chain, regulatory environment, trends, demand drivers, key players, and external forces.\n"
        "Do not propose solutions. Stick to facts, context, and explanations that help understand the ecosystem.\n"
    )
    try:
        raw = call_talos(INDUSTRY_URL, prompt, multiround_convo=max(1, req.multiround_convo or 1))
        html = format_compact_output(raw, body_line_height=1.30)
        return AnalyzeResponse(output_text=html, meta={
            "agent": "industry_research",
            "account": req.account,
            "industry": req.industry,
        })
    except requests.HTTPError as e:  # type: ignore[name-defined]
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# Agent: Company Research
# ================================

COMPANY_URL = (
    "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?"
    "society_id=1757657318406&agency_id=1762327921111&level=1"
)


@app.post("/api/agents/company-research/analyze", response_model=AnalyzeResponse)
def analyze_company(req: AnalyzeRequest):
    prompt = (
        f"{req.problem}\n\n"
        "To study and explain the company’s overall goals, vision, and direction with full clarity.\n"
        "To analyze all products, services, and operations in detail to understand how the company functions from end to end.\n"
        "To evaluate the company’s financial performance and market position over the past few years using reliable data and reports.\n"
        "To identify and explain the root causes of the company’s key problems, connecting them to both internal operations and external market factors."
    )
    try:
        raw = call_talos(COMPANY_URL, prompt, multiround_convo=max(1, req.multiround_convo or 1))
        html = format_compact_output(raw, body_line_height=1.30)
        return AnalyzeResponse(output_text=html, meta={
            "agent": "company_research",
            "account": req.account,
            "industry": req.industry,
        })
    except requests.HTTPError as e:  # type: ignore[name-defined]
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# Agent: Standard Practices
# ================================

STANDARD_PRACTICES_URL = (
    "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?"
    "society_id=1757657318406&agency_id=1762764462592&level=1"
)


@app.post("/api/agents/standard-practices/analyze", response_model=AnalyzeResponse)
def analyze_standard_practices(req: AnalyzeRequest):
    prompt = (
        f"{req.problem}\n\n"
        "Understand Industry Context\n"
        "Identify and summarize the standard practices, frameworks, and operational norms commonly followed within the industry related to the company’s problem statement.\n\n"
        "Assess Company Practices\n"
        "Examine how the specific company operates within its domain—its current strategies, processes, and business approaches that align with or differ from standard industry practices.\n\n"
        "Analyze Competitor Benchmarks\n"
        "Discover and analyze key competitors, exploring their best practices, innovative strategies, and differentiating factors that contribute to their market position or success.\n\n"
        "Synthesize Strategic Insights (Non-Solution Oriented)\n"
        "Consolidate findings into structured insights that reveal patterns, gaps, and opportunities for understanding—not for recommending solutions—helping decision-makers see the problem from a higher strategic lens."
    )
    try:
        raw = call_talos(STANDARD_PRACTICES_URL, prompt, multiround_convo=max(1, req.multiround_convo or 1))
        html = format_compact_output(raw, body_line_height=1.30)
        return AnalyzeResponse(output_text=html, meta={
            "agent": "standard_practices",
            "account": req.account,
            "industry": req.industry,
        })
    except requests.HTTPError as e:  # type: ignore[name-defined]
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# Agent: Identify Stakeholders
# ================================

STAKEHOLDERS_URL = (
    "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?"
    "society_id=1757657318406&agency_id=1759243465077&level=1"
)


@app.post("/api/agents/identify-stakeholders/analyze", response_model=AnalyzeResponse)
def analyze_stakeholders(req: AnalyzeRequest):
    prompt = (
        f"{req.problem}\n\n"
        "Identify and list all key stakeholders involved in this business problem. "
        "Categorize them by role, influence, and interest. "
        "Provide clear justification for each stakeholder's inclusion."
    )
    try:
        raw = call_talos(STAKEHOLDERS_URL, prompt, multiround_convo=max(1, req.multiround_convo or 1))
        html = format_compact_output(raw, body_line_height=1.30)
        return AnalyzeResponse(output_text=html, meta={
            "agent": "identify_stakeholders",
            "account": req.account,
            "industry": req.industry,
        })
    except requests.HTTPError as e:  # type: ignore[name-defined]
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# Agent: Question Discovery
# ================================

QUESTION_DISCOVERY_URL = (
    "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?"
    "society_id=1757657318406&agency_id=1760537932172&level=1"
)


@app.post("/api/agents/question-discovery/analyze", response_model=AnalyzeResponse)
def analyze_question_discovery(req: AnalyzeRequest):
    prompt = (
        f"{req.problem}\n\n"
        "To accurately interpret and contextualize any company's problem statement — identifying the underlying business area, objectives, and potential impact, rather than staying at the surface level.\n\n"
        "To reverse-engineer business reasoning by identifying hypotheses behind features, strategies, or decisions that may have led to the problem — linking cause and effect systematically.\n\n"
        "To generate meaningful, insight-driven business questions that stimulate investigation, innovation, and cross-functional collaboration — guiding teams toward solution discovery.\n\n"
        "To produce clear, organized, and reusable frameworks (summaries, hypotheses, linked features, and strategic questions) that support data analysis, strategy workshops, or consulting reports."
    )
    try:
        raw = call_talos(QUESTION_DISCOVERY_URL, prompt, multiround_convo=max(1, req.multiround_convo or 1))
        html = format_compact_output(raw, body_line_height=1.30)
        return AnalyzeResponse(output_text=html, meta={
            "agent": "question_discovery",
            "account": req.account,
            "industry": req.industry,
        })
    except requests.HTTPError as e:  # type: ignore[name-defined]
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# Agent: Problem Complexity
# ================================

PROBLEM_COMPLEXITY_URL = (
    "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?"
    "society_id=1757657318406&agency_id=1762852834267&level=1"
)


@app.post("/api/agents/problem-complexity/analyze", response_model=AnalyzeResponse)
def analyze_problem_complexity(req: AnalyzeRequest):
    prompt = (
        f"This is the problem statement: {req.problem}\n\n"
        "Reveal Hidden Complexity\n"
        "Identify the deeper structural, temporal, and behavioral interdependencies that are not immediately visible in the problem statement — uncovering what truly drives the issue beneath the surface.\n\n"
        "Elevate Problem Value\n"
        "Transform the problem from a simple or local issue into a strategic, high-leverage challenge that connects across functions, time horizons, and organizational systems — making it harder but more valuable to solve.\n\n"
        "Expose Boundary Expansion Opportunities\n"
        "Explicitly detect and articulate the boundaries of the current problem (organizational, temporal, cognitive, or systemic) and specify where those boundaries can be extended to unlock deeper insight or innovation potential.\n\n"
    )
    try:
        raw = call_talos(PROBLEM_COMPLEXITY_URL, prompt, multiround_convo=max(1, req.multiround_convo or 1))
        html = format_compact_output(raw, body_line_height=1.30)
        return AnalyzeResponse(output_text=html, meta={
            "agent": "problem_complexity",
            "account": req.account,
            "industry": req.industry,
        })
    except requests.HTTPError as e:  # type: ignore[name-defined]
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# Agent: Current System
# ================================

CURRENT_SYSTEM_URL = (
    "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?"
    "society_id=1757657318406&agency_id=1758549095254&level=1"
)


@app.post("/api/agents/current-system/analyze", response_model=AnalyzeResponse)
def analyze_current_system(req: AnalyzeRequest):
    vocab_output = (req.context or {}).get("vocabulary", "")
    prompt = (
        f"Problem statement - {req.problem}\n\n"
        f"Context from vocabulary:\n{vocab_output}\n\n"
        "Clearly describe the following sections, each starting with its heading:\n\n"
        "1. Core Business Problem:\n"
        "2. Current System:\n"
        "3. Inputs:\n"
        "4. Outputs:\n"
        "5. Pain Points:\n\n"
        "Ensure each section is clearly labeled exactly as shown."
    )
    try:
        raw_text = call_talos(CURRENT_SYSTEM_URL, prompt, multiround_convo=max(1, req.multiround_convo or 1))
        html = format_compact_output(raw_text, body_line_height=1.30)
        return AnalyzeResponse(output_text=html, meta={
            "agent": "current_system",
            "account": req.account,
            "industry": req.industry,
        })
    except requests.HTTPError as e:  # type: ignore[name-defined]
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# Agent: Volatility (Q1–Q3)
# ================================

VOL_Q1_URL = "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?society_id=1757657318406&agency_id=1758555344231&level=1"
VOL_Q2_URL = "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?society_id=1757657318406&agency_id=1758549615986&level=1"
VOL_Q3_URL = "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?society_id=1757657318406&agency_id=1758614550482&level=1"


@app.post("/api/agents/volatility/analyze", response_model=AnalyzeResponse)
def analyze_volatility(req: AnalyzeRequest):
    ctx = req.context or {}
    vocab_output = ctx.get("vocabulary", "")
    current_system_output = ctx.get("current_system", "")

    def mk_prompt(qtext: str) -> str:
        return (
            f"Problem statement - {req.problem}\n\n"
            f"Context from vocabulary:\n{vocab_output}\n\n"
            f"Context from current system:\n{current_system_output}\n\n"
            f"{qtext} Provide detailed analysis, score 0-5, and justification."
        )

    questions = [
        ("Q1", VOL_Q1_URL, "What is the frequency and pace of change in the key inputs driving the business?"),
        ("Q2", VOL_Q2_URL, "To what extent are these changes cyclical and predictable versus sporadic and unpredictable?"),
        ("Q3", VOL_Q3_URL, "How resilient is the current system in absorbing these changes without requiring significant rework or disruption?"),
    ]

    parts_html = []
    try:
        for name, url, qtext in questions:
            raw = call_talos(url, mk_prompt(qtext), multiround_convo=max(1, req.multiround_convo or 1))
            formatted = format_compact_output(raw, body_line_height=1.30)
            parts_html.append(f"<div style='margin:12px 0'><h4 style='color:#8b1e1e;margin:0 0 6px'>{name}</h4>{formatted}</div>")

        combined = (
            "<div>"
            "<div class=\"section-title-box\" style=\"padding:1rem 1.5rem; background:#8b1e1e; border-radius:12px; color:white; margin-bottom:8px;\">"
            "<h3 style=\"margin:0; font-weight:800; font-size:1.2rem;\">Volatility Analysis</h3>"
            "</div>" + "".join(parts_html) + "</div>"
        )

        return AnalyzeResponse(output_text=combined, meta={
            "agent": "volatility",
            "account": req.account,
            "industry": req.industry,
        })
    except requests.HTTPError as e:  # type: ignore[name-defined]
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# Agent: Ambiguity (Q4–Q6)
# ================================

AMB_Q4_URL = "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?society_id=1757657318406&agency_id=1758614809984&level=1"
AMB_Q5_URL = "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?society_id=1757657318406&agency_id=1758615038050&level=1"
AMB_Q6_URL = "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?society_id=1757657318406&agency_id=1758615386880&level=1"


@app.post("/api/agents/ambiguity/analyze", response_model=AnalyzeResponse)
def analyze_ambiguity(req: AnalyzeRequest):
    ctx = req.context or {}
    vocab_output = ctx.get("vocabulary", "")
    current_system_output = ctx.get("current_system", "")

    def mk_prompt(qtext: str) -> str:
        return (
            f"Problem statement - {req.problem}\n\n"
            f"Context from Vocabulary:\n{vocab_output}\n\n"
            f"Context from Current System:\n{current_system_output}\n\n"
            f"{qtext} Score 0-5. Provide justification."
        )

    questions = [
        ("Q4", AMB_Q4_URL, "To what extent do stakeholders share a common understanding and goals about the problem?"),
        ("Q5", AMB_Q5_URL, "Are there significant conflicts or tradeoffs between stakeholders or system elements?"),
        ("Q6", AMB_Q6_URL, "How clear is the problem definition and scope?"),
    ]

    parts_html = []
    try:
        for name, url, qtext in questions:
            raw = call_talos(url, mk_prompt(qtext), multiround_convo=max(1, req.multiround_convo or 1))
            formatted = format_compact_output(raw, body_line_height=1.30)
            parts_html.append(f"<div style='margin:12px 0'><h4 style='color:#8b1e1e;margin:0 0 6px'>{name}</h4>{formatted}</div>")

        combined = (
            "<div>"
            "<div class=\"section-title-box\" style=\"padding:1rem 1.5rem; background:#8b1e1e; border-radius:12px; color:white; margin-bottom:8px;\">"
            "<h3 style=\"margin:0; font-weight:800; font-size:1.2rem;\">Ambiguity Analysis</h3>"
            "</div>" + "".join(parts_html) + "</div>"
        )

        return AnalyzeResponse(output_text=combined, meta={
            "agent": "ambiguity",
            "account": req.account,
            "industry": req.industry,
        })
    except requests.HTTPError as e:  # type: ignore[name-defined]
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# Agent: Interconnectedness (Q7–Q9)
# ================================

INT_Q7_URL = "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?society_id=1757657318406&agency_id=1758615778653&level=1"
INT_Q8_URL = "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?society_id=1757657318406&agency_id=1758616081630&level=1"
INT_Q9_URL = "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?society_id=1757657318406&agency_id=1758616793510&level=1"


@app.post("/api/agents/interconnectedness/analyze", response_model=AnalyzeResponse)
def analyze_interconnectedness(req: AnalyzeRequest):
    ctx = req.context or {}
    vocab_output = ctx.get("vocabulary", "")
    current_system_output = ctx.get("current_system", "")

    def mk_prompt(qtext: str) -> str:
        return (
            f"Problem statement - {req.problem}\n\n"
            f"Context from Vocabulary:\n{vocab_output}\n\n"
            f"Context from Current System:\n{current_system_output}\n\n"
            f"{qtext} Score 0-5. Provide justification."
        )

    questions = [
        ("Q7", INT_Q7_URL, "How interdependent are the components, processes, and stakeholders involved?"),
        ("Q8", INT_Q8_URL, "How quickly do changes in one part of the system propagate to other parts?"),
        ("Q9", INT_Q9_URL, "What is the degree of coordination required across teams/systems to achieve outcomes?"),
    ]

    parts_html = []
    try:
        for name, url, qtext in questions:
            raw = call_talos(url, mk_prompt(qtext), multiround_convo=max(1, req.multiround_convo or 1))
            formatted = format_compact_output(raw, body_line_height=1.30)
            parts_html.append(f"<div style='margin:12px 0'><h4 style='color:#8b1e1e;margin:0 0 6px'>{name}</h4>{formatted}</div>")

        combined = (
            "<div>"
            "<div class=\"section-title-box\" style=\"padding:1rem 1.5rem; background:#8b1e1e; border-radius:12px; color:white; margin-bottom:8px;\">"
            "<h3 style=\"margin:0; font-weight:800; font-size:1.2rem;\">Interconnectedness Analysis</h3>"
            "</div>" + "".join(parts_html) + "</div>"
        )

        return AnalyzeResponse(output_text=combined, meta={
            "agent": "interconnectedness",
            "account": req.account,
            "industry": req.industry,
        })
    except requests.HTTPError as e:  # type: ignore[name-defined]
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# Agent: Uncertainty (Q10–Q12)
# ================================

UNC_Q10_URL = "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?society_id=1757657318406&agency_id=1758617140479&level=1"
UNC_Q11_URL = "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?society_id=1757657318406&agency_id=1758618137301&level=1"
UNC_Q12_URL = "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?society_id=1757657318406&agency_id=1758619317968&level=1"


@app.post("/api/agents/uncertainty/analyze", response_model=AnalyzeResponse)
def analyze_uncertainty(req: AnalyzeRequest):
    ctx = req.context or {}
    vocab_output = ctx.get("vocabulary", "")
    current_system_output = ctx.get("current_system", "")

    def mk_prompt(qtext: str) -> str:
        return (
            f"Problem statement - {req.problem}\n\n"
            f"Context from Vocabulary:\n{vocab_output}\n\n"
            f"Context from Current System:\n{current_system_output}\n\n"
            f"{qtext} Score 0-5. Provide justification."
        )

    questions = [
        ("Q10", UNC_Q10_URL, "How incomplete or noisy are the available data inputs?"),
        ("Q11", UNC_Q11_URL, "How uncertain are the causal relationships between inputs and outcomes?"),
        ("Q12", UNC_Q12_URL, "How often do events occur that were not anticipated by current models or processes?"),
    ]

    parts_html = []
    try:
        for name, url, qtext in questions:
            raw = call_talos(url, mk_prompt(qtext), multiround_convo=max(1, req.multiround_convo or 1))
            formatted = format_compact_output(raw, body_line_height=1.30)
            parts_html.append(f"<div style='margin:12px 0'><h4 style='color:#8b1e1e;margin:0 0 6px'>{name}</h4>{formatted}</div>")

        combined = (
            "<div>"
            "<div class=\"section-title-box\" style=\"padding:1rem 1.5rem; background:#8b1e1e; border-radius:12px; color:white; margin-bottom:8px;\">"
            "<h3 style=\"margin:0; font-weight:800; font-size:1.2rem;\">Uncertainty Analysis</h3>"
            "</div>" + "".join(parts_html) + "</div>"
        )

        return AnalyzeResponse(output_text=combined, meta={
            "agent": "uncertainty",
            "account": req.account,
            "industry": req.industry,
        })
    except requests.HTTPError as e:  # type: ignore[name-defined]
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
