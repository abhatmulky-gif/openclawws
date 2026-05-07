"""
Base skill abstraction for the ASTRA assessment assistant.

Each skill is a self-contained assessment covering one TM Forum use case.
Skills define sub-scenarios, criteria, options, and scoring logic.
The orchestrator calls into these objects to drive the conversation.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SubScenario:
    id: str
    name: str
    description: str
    weight: float        # 0.0–1.0; all scenario weights must sum to 1.0


@dataclass
class CriterionOption:
    level: int           # 0–5 (L0–L5)
    label: str           # short label shown on button
    description: str     # full description for the card
    keywords: list = field(default_factory=list)  # for stub-mode keyword matching


@dataclass
class Criterion:
    id: str
    name: str
    question: str
    cognitive_activity: str   # Intent / Awareness / Analysis / Decision / Execution
    weight: float             # relative weight within this skill (0.0–1.0)
    options: list             # list[CriterionOption]
    evidence_prompt: str = "" # follow-up: "Briefly describe how your system does this"
    scenario_specific: bool = True  # False = one answer applies to all scenarios


# ---------------------------------------------------------------------------
# Base skill
# ---------------------------------------------------------------------------

class BaseSkill:
    """
    Override id, name, description, icon, scenarios, and criteria in subclasses.
    All scoring and conversation-state logic lives here.
    """

    id: str = "base"
    name: str = "Base Skill"
    description: str = ""
    icon: str = "🔧"
    scenarios: list = []    # list[SubScenario]
    criteria: list = []     # list[Criterion]

    # ------------------------------------------------------------------ #
    # Intro / context                                                     #
    # ------------------------------------------------------------------ #

    def get_intro_message(self) -> str:
        scenario_list = "\n".join(
            f"  • **{s.name}** ({int(s.weight * 100)}%) — {s.description}"
            for s in self.scenarios
        )
        return (
            f"## {self.name}\n\n"
            f"{self.description}\n\n"
            f"**Assessment structure:** {len(self.criteria)} criteria across "
            f"{len(self.scenarios)} sub-scenario(s):\n{scenario_list}\n\n"
            f"Scoring: L0 (Manual) → L5 (Cognitive Autonomous) per TM Forum IG1218 v2.2.0.\n\n"
            f"Each question presents 4–6 options. Select the one that **best describes your "
            f"current system's capability** — not your target.\n\n"
            f"Let's begin with **{self.criteria[0].cognitive_activity}**."
        )

    # ------------------------------------------------------------------ #
    # State machine helpers                                               #
    # ------------------------------------------------------------------ #

    def _scenario_ids(self) -> list:
        if not self.scenarios:
            return ["_default"]
        return [s.id for s in self.scenarios]

    def _criteria_for_scenario(self, scenario_id: str) -> list:
        """All criteria apply to all scenarios by default."""
        return self.criteria

    def initial_state(self) -> dict:
        return {
            "scenario_idx":  0,
            "criterion_idx": 0,
            "awaiting_evidence": False,
            "answers": {},        # {criterion_id: {scenario_id: {"level": int, "text": str}}}
            "contact": {},
            "history": [],
        }

    def current_position(self, state: dict) -> tuple:
        """Returns (scenario_id, criterion) for the current position."""
        scn_ids = self._scenario_ids()
        scn_idx = state.get("scenario_idx", 0)
        crit_idx = state.get("criterion_idx", 0)
        scn_id = scn_ids[scn_idx] if scn_idx < len(scn_ids) else None
        crit = self.criteria[crit_idx] if crit_idx < len(self.criteria) else None
        return scn_id, crit

    def is_complete(self, state: dict) -> bool:
        # advance() always resets scenario_idx to 0 when moving to next criterion,
        # so we only need to check whether we've passed the last criterion.
        return state.get("criterion_idx", 0) >= len(self.criteria)

    def advance(self, state: dict) -> dict:
        """Move to the next (criterion × scenario) position."""
        scn_ids = self._scenario_ids()
        scn_idx = state.get("scenario_idx", 0)
        crit_idx = state.get("criterion_idx", 0)

        crit = self.criteria[crit_idx]
        if crit.scenario_specific:
            # Advance scenario first; when all scenarios done → next criterion
            next_scn = scn_idx + 1
            if next_scn < len(scn_ids):
                return {**state, "scenario_idx": next_scn, "awaiting_evidence": False}
        # Move to next criterion, reset scenario
        return {**state, "scenario_idx": 0, "criterion_idx": crit_idx + 1,
                "awaiting_evidence": False}

    def record_answer(self, state: dict, level: int, text: str) -> dict:
        scn_id, crit = self.current_position(state)
        answers = {**state.get("answers", {})}
        if crit.id not in answers:
            answers[crit.id] = {}
        answers[crit.id][scn_id] = {"level": level, "text": text}
        new_state = {**state, "answers": answers}
        if crit.evidence_prompt:
            new_state["awaiting_evidence"] = True
        else:
            new_state = self.advance(new_state)
        return new_state

    def record_evidence(self, state: dict, evidence_text: str) -> dict:
        scn_id, crit = self.current_position(state)
        answers = {**state.get("answers", {})}
        if crit.id in answers and scn_id in answers[crit.id]:
            answers[crit.id][scn_id]["evidence"] = evidence_text
        return self.advance({**state, "answers": answers, "awaiting_evidence": False})

    # ------------------------------------------------------------------ #
    # Question rendering                                                  #
    # ------------------------------------------------------------------ #

    def render_question(self, state: dict) -> dict:
        """Returns a dict the chat UI can render: message text + option cards."""
        scn_id, crit = self.current_position(state)

        # Progress indicator
        crit_idx = state.get("criterion_idx", 0)
        scn_idx  = state.get("scenario_idx", 0)
        total_steps = len(self.criteria) * max(1, len(self.scenarios))
        done_steps  = crit_idx * max(1, len(self.scenarios)) + scn_idx
        pct = int(done_steps / total_steps * 100)

        scenario_label = ""
        if self.scenarios:
            scn = next((s for s in self.scenarios if s.id == scn_id), None)
            scenario_label = f"*Sub-scenario: {scn.name} ({int(scn.weight*100)}%)*\n\n" if scn else ""

        prev_crit_id = self.criteria[crit_idx - 1].id if crit_idx > 0 else None
        activity_changed = (
            crit_idx == 0 or
            self.criteria[crit_idx].cognitive_activity !=
            self.criteria[crit_idx - 1].cognitive_activity
        ) and scn_idx == 0

        activity_header = ""
        if activity_changed:
            activity_header = f"### {crit.cognitive_activity}\n\n"

        text = (
            f"{activity_header}"
            f"**Q{done_steps + 1}/{total_steps} · {crit.name}**\n\n"
            f"{scenario_label}"
            f"{crit.question}"
        )

        return {
            "type":      "question",
            "text":      text,
            "progress":  pct,
            "criterion": crit.id,
            "scenario":  scn_id,
            "options":   [
                {"level": o.level, "label": o.label, "description": o.description}
                for o in crit.options
            ],
            "can_skip": True,
        }

    def render_evidence_prompt(self, state: dict) -> dict:
        _, crit = self.current_position(state)
        return {
            "type":   "evidence",
            "text":   crit.evidence_prompt or "Briefly describe how your system handles this.",
            "skip_label": "Skip — move to next question",
        }

    # ------------------------------------------------------------------ #
    # Scoring                                                             #
    # ------------------------------------------------------------------ #

    def calculate_scores(self, state: dict) -> dict:
        """
        Returns {
            "dimensions": {"Intent": 3.2, "Awareness": 2.1, ...},
            "overall":    2.8,
            "criteria":   {criterion_id: weighted_score},
        }
        """
        answers = state.get("answers", {})
        scn_ids = self._scenario_ids()

        # Per-scenario weights
        scn_weights = {s.id: s.weight for s in self.scenarios} if self.scenarios else {"_default": 1.0}

        dimension_sums: dict[str, float] = {}
        dimension_weights: dict[str, float] = {}
        criteria_scores: dict[str, float] = {}

        for crit in self.criteria:
            crit_ans = answers.get(crit.id, {})
            if not crit_ans:
                continue

            if crit.scenario_specific:
                weighted_level = sum(
                    crit_ans[sid]["level"] * scn_weights.get(sid, 0)
                    for sid in scn_ids if sid in crit_ans
                )
            else:
                first = next(iter(crit_ans.values()), {})
                weighted_level = first.get("level", 0)

            criteria_scores[crit.id] = round(weighted_level, 2)
            dim = crit.cognitive_activity
            dimension_sums[dim] = dimension_sums.get(dim, 0) + weighted_level * crit.weight
            dimension_weights[dim] = dimension_weights.get(dim, 0) + crit.weight

        dimensions = {
            dim: round(dimension_sums[dim] / dimension_weights[dim], 2)
            for dim in dimension_sums
            if dimension_weights.get(dim, 0) > 0
        }
        overall = round(
            sum(dimensions.values()) / len(dimensions), 2
        ) if dimensions else 0.0

        return {
            "skill":      self.id,
            "dimensions": dimensions,
            "overall":    overall,
            "criteria":   criteria_scores,
        }

    # ------------------------------------------------------------------ #
    # Stub summary (no LLM)                                               #
    # ------------------------------------------------------------------ #

    def generate_summary(self, scores: dict, contact: dict) -> str:
        overall = scores.get("overall", 0)
        dims = scores.get("dimensions", {})
        company = contact.get("company", "your organisation")

        level_labels = {
            0: "L0 — Manual",
            1: "L1 — Assisted",
            2: "L2 — Partial Automation",
            3: "L3 — Conditional Autonomy",
            4: "L4 — Highly Autonomous",
            5: "L5 — Cognitive Autonomous",
        }
        level = level_labels.get(min(5, int(overall)), "L0 — Manual")

        weakest = min(dims, key=dims.get) if dims else "—"
        strongest = max(dims, key=dims.get) if dims else "—"

        return (
            f"## Assessment Complete — {company}\n\n"
            f"**Overall Autonomy Level: {level}** (score: {overall:.1f}/5.0)\n\n"
            f"Your strongest dimension is **{strongest}** "
            f"({dims.get(strongest, 0):.1f}/5.0), and the biggest opportunity "
            f"is **{weakest}** ({dims.get(weakest, 0):.1f}/5.0).\n\n"
            f"Your full report with benchmark comparison and Svaya recommendations "
            f"is ready to download."
        )
