"""
Conversation orchestrator.

Drives the assessment state machine. Supports two modes:
  - Stub mode (no ANTHROPIC_API_KEY): presents clickable option cards only.
  - LLM mode: accepts free text, uses Claude Haiku to map to L0–L5, uses
    Claude Sonnet for report narrative generation.

The orchestrator is stateless — all state lives in the session (SQLite).
Each call returns a list of message dicts for the front-end to render.
"""

import os
import sys
from typing import Optional

# Ensure parent dir on path for direct imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bot.session import (
    create_session, get_session, save_session, update_state
)
from bot.skill_registry import get_skill, skill_menu
from lead_store import save_lead
from network_probe import run_probe, probe_to_dict
from survey_engine import score_answers     # quick-score fallback for survey skill

# ---------------------------------------------------------------------------
# Optional LLM integration
# ---------------------------------------------------------------------------

_ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")
_llm_client = None

if _ANTHROPIC_KEY:
    try:
        import anthropic
        _llm_client = anthropic.Anthropic(api_key=_ANTHROPIC_KEY)
    except ImportError:
        pass


def _haiku(system: str, user: str, max_tokens: int = 512) -> str:
    """Call Claude Haiku. Returns empty string if LLM unavailable."""
    if not _llm_client:
        return ""
    try:
        resp = _llm_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return resp.content[0].text.strip()
    except Exception:
        return ""


def _sonnet(system: str, user: str, max_tokens: int = 1024) -> str:
    """Call Claude Sonnet for richer report narrative."""
    if not _llm_client:
        return ""
    try:
        resp = _llm_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return resp.content[0].text.strip()
    except Exception:
        return ""


def _llm_score_answer(options: list, free_text: str) -> int:
    """
    Use Haiku to map a free-text answer to an L0–L5 level.
    Falls back to -1 (no match) if LLM unavailable.
    """
    if not _llm_client or not free_text.strip():
        return -1
    options_str = "\n".join(
        f"Level {o['level']} ({o['label']}): {o['description']}"
        for o in options
    )
    system = (
        "You are scoring network automation maturity. Given a question's options "
        "and an operator's free-text answer, return ONLY the integer level (0–5) "
        "that best matches their answer. Return exactly one integer."
    )
    result = _haiku(system, f"Options:\n{options_str}\n\nOperator answer: {free_text}")
    try:
        return int(result.strip())
    except ValueError:
        return -1


# ---------------------------------------------------------------------------
# Message builders
# ---------------------------------------------------------------------------

def _msg(role: str, content: str, **extra) -> dict:
    return {"role": role, "content": content, **extra}


def _assistant(content: str, **extra) -> dict:
    return _msg("assistant", content, **extra)


def _welcome_message() -> dict:
    skills = skill_menu()
    return _assistant(
        "## Welcome to the Svaya Network Autonomy Assessment\n\n"
        "I'll guide you through a structured assessment of your network's "
        "automation maturity — aligned with TM Forum IG1218 v2.2.0 and IG1252 v1.2.0.\n\n"
        "**Select an assessment to begin:**",
        type="skill_select",
        skills=skills,
    )


def _contact_prompt() -> dict:
    return _assistant(
        "Almost done! Please tell me a few details so I can prepare your full report.",
        type="contact_form",
        fields=[
            {"id": "company",      "label": "Company",      "type": "text",  "required": True},
            {"id": "contact_name", "label": "Your Name",    "type": "text",  "required": True},
            {"id": "email",        "label": "Work Email",   "type": "email", "required": True},
            {"id": "phone",        "label": "Phone",        "type": "tel",   "required": False},
        ],
    )


# ---------------------------------------------------------------------------
# Main orchestration entry points
# ---------------------------------------------------------------------------

def start_session() -> tuple:
    """Create a new session and return (session_id, welcome_message)."""
    sid = create_session()
    return sid, _welcome_message()


def handle_skill_select(sid: str, skill_id: str) -> list:
    """Operator selected a skill from the menu."""
    skill = get_skill(skill_id)
    if not skill:
        return [_assistant(f"Sorry, skill '{skill_id}' not found. Please choose from the menu.",
                           type="skill_select", skills=skill_menu())]

    initial_state = skill.initial_state()
    save_session(sid, skill_id, "in_progress", initial_state)

    intro = _assistant(skill.get_intro_message(), type="markdown")
    first_q = skill.render_question(initial_state)
    return [intro, _assistant(first_q["text"], type="question",
                               progress=first_q["progress"],
                               options=first_q["options"],
                               criterion=first_q["criterion"],
                               scenario=first_q["scenario"])]


def handle_option_select(sid: str, criterion_id: str, scenario_id: str,
                         level: int, option_text: str) -> list:
    """Operator clicked an option card."""
    sess = get_session(sid)
    if not sess or sess["phase"] != "in_progress":
        return [_assistant("Session not found. Please refresh.", type="error")]

    skill = get_skill(sess["skill_id"])
    if not skill:
        return [_assistant("Skill error.", type="error")]

    state = sess["state"]
    new_state = skill.record_answer(state, level, option_text)
    save_session(sid, sess["skill_id"], "in_progress", new_state)

    if new_state.get("awaiting_evidence"):
        _, crit = skill.current_position(new_state)
        # Advance position for evidence phase but don't re-record answer
        ev_q = skill.render_evidence_prompt(new_state)
        return [_assistant(ev_q["text"], type="evidence",
                           criterion=criterion_id, scenario=scenario_id)]

    return _next_turn(sid, skill, new_state)


def handle_evidence(sid: str, criterion_id: str, scenario_id: str,
                    evidence_text: str) -> list:
    """Operator provided (or skipped) evidence for the last answer."""
    sess = get_session(sid)
    if not sess:
        return [_assistant("Session not found.", type="error")]
    skill = get_skill(sess["skill_id"])
    state = sess["state"]
    new_state = skill.record_evidence(state, evidence_text)
    save_session(sid, sess["skill_id"], "in_progress", new_state)
    return _next_turn(sid, skill, new_state)


def handle_free_text(sid: str, text: str) -> list:
    """Operator typed a free-text message (LLM mode or contact fields)."""
    sess = get_session(sid)
    if not sess:
        return [_assistant("Session not found. Please refresh.", type="error")]

    phase = sess["phase"]
    state = sess["state"]

    # ── Contact collection ──
    if phase == "contact":
        return [_assistant("Please use the contact form above to submit your details.",
                           type="hint")]

    if phase != "in_progress":
        return [_assistant("Please select an assessment to begin.",
                           type="skill_select", skills=skill_menu())]

    skill = get_skill(sess["skill_id"])
    if not skill:
        return [_assistant("Skill error.", type="error")]

    # Evidence phase: treat any text as evidence
    if state.get("awaiting_evidence"):
        return handle_evidence(sid, "", "", text)

    # Try LLM scoring
    _, crit = skill.current_position(state)
    if crit is None:
        return _finalise(sid, skill, state)

    options = [{"level": o.level, "label": o.label, "description": o.description}
               for o in crit.options]
    level = _llm_score_answer(options, text)
    if level >= 0:
        option_text = next(
            (o.description for o in crit.options if o.level == level),
            text
        )
        return handle_option_select(sid, crit.id, state.get("scenario_idx", ""), level, option_text)

    # Cannot score — ask to use buttons
    return [_assistant(
        "I couldn't match that to a scoring level. "
        "Please use the option buttons to answer.",
        type="hint",
    )]


def handle_contact_submit(sid: str, contact: dict) -> list:
    """Operator submitted contact form — finalise and save lead."""
    sess = get_session(sid)
    if not sess:
        return [_assistant("Session not found.", type="error")]

    skill = get_skill(sess["skill_id"])
    state = {**sess["state"], "contact": contact}
    save_session(sid, sess["skill_id"], "contact", state)

    scores = skill.calculate_scores(state)
    summary = skill.generate_summary(scores, contact)

    # Build scores dict compatible with lead_store and report_gen
    lead_scores = {
        "domains":         scores.get("dimensions", {}),
        "overall":         scores.get("overall", 0),
        "level":           _level_label(scores.get("overall", 0)),
        "gaps":            [],
        "recommendations": [],
    }

    lead_id = save_lead(
        company=contact.get("company", ""),
        contact_name=contact.get("contact_name", ""),
        email=contact.get("email", ""),
        phone=contact.get("phone", ""),
        country=contact.get("country", ""),
        network_size=contact.get("network_size", ""),
        answers=state.get("answers", {}),
        scores=lead_scores,
        probe_result=state.get("probe_result"),
    )

    save_session(sid, sess["skill_id"], "complete", {**state, "lead_id": lead_id})

    return [
        _assistant(summary, type="markdown"),
        _assistant("", type="result_cta", lead_id=lead_id),
    ]


# ---------------------------------------------------------------------------
# Network probe skill special flow
# ---------------------------------------------------------------------------

def handle_probe_inputs(sid: str, inputs: dict) -> list:
    """Run live probe and return results in-chat."""
    endpoint = inputs.get("nms_endpoint", "").strip()
    vendor   = inputs.get("nms_vendor", "generic").strip()
    pm_user  = inputs.get("pm_username", "").strip()
    pm_pass  = inputs.get("pm_password", "").strip()

    if not endpoint:
        return [_assistant("Please provide the NMS endpoint URL.", type="hint")]

    thinking = _assistant("Running probe — this takes up to 30 seconds…", type="thinking")

    try:
        report = run_probe(endpoint, vendor, pm_user, pm_pass)
        result = probe_to_dict(report)
    except Exception as e:
        result = {"error": str(e), "nms_readiness": "UNREACHABLE", "summary": str(e)}

    sess = get_session(sid)
    if sess:
        new_state = {**sess["state"], "probe_result": result}
        save_session(sid, sess["skill_id"], sess["phase"], new_state)

    return [thinking, _assistant("", type="probe_result", probe=result), _contact_prompt()]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _next_turn(sid: str, skill, state: dict) -> list:
    if skill.is_complete(state):
        save_session(sid, skill.id, "contact", state)
        return [_contact_prompt()]

    q = skill.render_question(state)
    return [_assistant(q["text"], type="question",
                       progress=q["progress"],
                       options=q["options"],
                       criterion=q["criterion"],
                       scenario=q["scenario"])]


def _finalise(sid: str, skill, state: dict) -> list:
    save_session(sid, skill.id, "contact", state)
    return [_contact_prompt()]


def _level_label(score: float) -> str:
    labels = {0: "L0 — Manual", 1: "L1 — Assisted", 2: "L2 — Partial Automation",
              3: "L3 — Conditional Autonomy", 4: "L4 — Highly Autonomous",
              5: "L5 — Cognitive Autonomous"}
    return labels.get(min(5, int(score)), "L0 — Manual")
