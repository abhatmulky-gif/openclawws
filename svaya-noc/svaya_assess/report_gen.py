"""
PDF report generator using fpdf2.
Produces a branded Svaya assessment report with:
  - Cover page (operator details, overall maturity badge)
  - Per-domain maturity bars vs. industry benchmark
  - Svaya gap analysis and prioritised recommendations
  - Network probe results (if run)
  - Next steps / CTA
"""

import io
from typing import Optional

try:
    from fpdf import FPDF, XPos, YPos
    _FPDF_AVAILABLE = True
except ImportError:
    _FPDF_AVAILABLE = False

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
_C = {
    "svaya_blue":   (0,   80,  160),
    "svaya_teal":   (0,  180,  160),
    "bg_light":     (245, 248, 252),
    "border":       (200, 215, 230),
    "text_dark":    (30,  40,   55),
    "text_mid":     (80,  100, 120),
    "green":        (34,  197,  94),
    "amber":        (245, 158,  11),
    "red":          (239,  68,  68),
    "white":        (255, 255, 255),
    "bar_fill":     (0,  140, 200),
    "bar_bench":    (200, 215, 230),
}

_LEVEL_COLORS = {
    0: (180, 180, 180),
    1: (239,  68,  68),
    2: (245, 158,  11),
    3: (34,  140,  80),
    4: (0,   80,  160),
}

_READINESS_COLORS = {
    "READY":        (34,  197,  94),
    "PARTIAL":      (245, 158,  11),
    "NEEDS_CONFIG": (249, 115,  22),
    "UNREACHABLE":  (239,  68,  68),
}


# ---------------------------------------------------------------------------
# FPDF subclass
# ---------------------------------------------------------------------------

class _Report(FPDF):
    def header(self):
        self.set_fill_color(*_C["svaya_blue"])
        self.rect(0, 0, 210, 12, "F")
        self.set_xy(10, 2)
        self.set_text_color(*_C["white"])
        self.set_font("Helvetica", "B", 9)
        self.cell(0, 8, "ASTRA Network Autonomy Assessment  |  Svaya", align="L")
        self.set_text_color(*_C["text_dark"])
        self.ln(14)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*_C["text_mid"])
        self.cell(0, 10, f"Page {self.page_no()}  |  Confidential — Svaya Networks  |  svaya.io",
                  align="C")


# ---------------------------------------------------------------------------
# Section helpers
# ---------------------------------------------------------------------------

def _section_title(pdf: _Report, text: str) -> None:
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*_C["svaya_blue"])
    pdf.set_fill_color(*_C["bg_light"])
    pdf.cell(0, 8, text, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)
    pdf.set_text_color(*_C["text_dark"])


def _bar(pdf: _Report, label: str, score: float, benchmark: float, max_score: float = 4.0) -> None:
    BAR_W = 110
    BAR_H = 6
    x0 = pdf.get_x()
    y0 = pdf.get_y()

    # Label
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*_C["text_dark"])
    pdf.cell(52, BAR_H + 4, label)

    # Background track
    bx = x0 + 52
    pdf.set_fill_color(*_C["bar_bench"])
    pdf.rect(bx, y0 + 1, BAR_W, BAR_H, "F")

    # Score fill
    fill_w = (score / max_score) * BAR_W
    pdf.set_fill_color(*_C["bar_fill"])
    pdf.rect(bx, y0 + 1, fill_w, BAR_H, "F")

    # Benchmark tick
    bench_x = bx + (benchmark / max_score) * BAR_W
    pdf.set_draw_color(*_C["text_mid"])
    pdf.set_line_width(0.4)
    pdf.line(bench_x, y0, bench_x, y0 + BAR_H + 2)

    # Score label
    pdf.set_xy(bx + BAR_W + 3, y0)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(20, BAR_H + 2, f"L{score:.1f}", align="L")

    pdf.set_xy(x0, y0 + BAR_H + 4)


def _probe_status_dot(pdf: _Report, status: str) -> None:
    colors = {"ok": _C["green"], "warn": _C["amber"], "fail": _C["red"], "skip": _C["text_mid"]}
    labels = {"ok": "OK", "warn": "WARN", "fail": "FAIL", "skip": "SKIP"}
    c = colors.get(status, _C["text_mid"])
    pdf.set_fill_color(*c)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*_C["white"])
    pdf.cell(14, 5, labels.get(status, status.upper()), fill=True, align="C")
    pdf.set_text_color(*_C["text_dark"])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_pdf(
    company: str,
    contact_name: str,
    email: str,
    scores: dict,
    probe_result: Optional[dict] = None,
    lead_id: Optional[str] = None,
) -> bytes:
    """
    Generate the assessment PDF and return raw bytes.
    Falls back to a plain-text stub if fpdf2 is not installed.
    """
    if not _FPDF_AVAILABLE:
        return _text_fallback(company, contact_name, scores, probe_result)

    pdf = _Report(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(15, 18, 15)

    # -----------------------------------------------------------------------
    # Cover page
    # -----------------------------------------------------------------------
    pdf.add_page()

    # Hero band
    pdf.set_fill_color(*_C["svaya_blue"])
    pdf.rect(0, 12, 210, 55, "F")
    pdf.set_xy(15, 22)
    pdf.set_text_color(*_C["white"])
    pdf.set_font("Helvetica", "B", 22)
    pdf.cell(0, 12, "Network Autonomy Assessment", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(15)
    pdf.set_font("Helvetica", "", 14)
    pdf.cell(0, 8, "TM Forum eTOM Alignment Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(15)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"Prepared for: {company}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Maturity badge
    level = scores.get("overall", 0)
    level_label = scores.get("level", "L0 Manual")
    badge_color = _LEVEL_COLORS.get(int(level), _LEVEL_COLORS[0])
    pdf.set_xy(140, 22)
    pdf.set_fill_color(*badge_color)
    pdf.rect(140, 20, 55, 46, "F")
    pdf.set_xy(140, 27)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*_C["white"])
    pdf.cell(55, 6, "OVERALL MATURITY", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(140)
    pdf.set_font("Helvetica", "B", 34)
    pdf.cell(55, 20, f"L{int(level)}", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(140)
    pdf.set_font("Helvetica", "", 8)
    pdf.multi_cell(55, 5, level_label, align="C")

    pdf.set_text_color(*_C["text_dark"])
    pdf.set_xy(15, 72)

    # Contact block
    pdf.set_font("Helvetica", "", 10)
    pdf.set_fill_color(*_C["bg_light"])
    pdf.rect(15, 74, 120, 22, "F")
    pdf.set_xy(18, 77)
    pdf.cell(0, 6, f"Contact: {contact_name}  |  {email}")
    if lead_id:
        pdf.set_xy(18, 84)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*_C["text_mid"])
        pdf.cell(0, 5, f"Assessment ID: {lead_id}")
        pdf.set_text_color(*_C["text_dark"])

    pdf.ln(28)

    # Executive summary blurb
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "What this report covers", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*_C["text_mid"])
    pdf.multi_cell(
        0, 5,
        "This report benchmarks your network operations against the TM Forum Autonomous Networks "
        "framework (IG1218 / IG1230). It scores your current autonomy level across five eTOM "
        "domains, identifies gaps where Svaya ASTRA can accelerate your automation journey, and "
        "(where consented) summarises the results of a live network readiness probe.",
    )
    pdf.set_text_color(*_C["text_dark"])
    pdf.ln(4)

    # -----------------------------------------------------------------------
    # Page 2 — Maturity scores
    # -----------------------------------------------------------------------
    pdf.add_page()
    _section_title(pdf, "TM Forum Autonomy Maturity by eTOM Domain")

    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*_C["text_mid"])
    pdf.cell(52, 5, "Domain")
    pdf.cell(110, 5, "Score vs. Industry Benchmark  (tick = avg, L0–L4)")
    pdf.cell(20, 5, "Score")
    pdf.ln(5)
    pdf.set_text_color(*_C["text_dark"])

    from survey_engine import BENCHMARKS, DOMAIN_LABELS
    domain_scores = scores.get("domains", {})

    for domain, label in DOMAIN_LABELS.items():
        score = domain_scores.get(domain, 0)
        bench = BENCHMARKS.get(domain, {}).get("avg", 1.2)
        _bar(pdf, label, score, bench)
        pdf.ln(3)

    pdf.ln(4)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*_C["text_mid"])
    pdf.cell(0, 5, "Tick mark (|) indicates industry average. Top-quartile operators score ≥2.5.")
    pdf.set_text_color(*_C["text_dark"])
    pdf.ln(8)

    # Level descriptions
    _section_title(pdf, "Autonomy Level Reference")
    levels = [
        ("L0", "Manual",         "All operations require human intervention."),
        ("L1", "Assisted",       "Monitoring with rule-based alerts; human acts on recommendations."),
        ("L2", "Partial",        "Closed-loop automation for routine tasks; humans handle exceptions."),
        ("L3", "Conditional",    "Intent-based automation; operator approves edge cases."),
        ("L4", "Full Autonomy",  "Self-optimising network; operator monitors outcomes only."),
    ]
    for lv, name, desc in levels:
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(14, 6, lv)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*_C["svaya_blue"])
        pdf.cell(26, 6, name)
        pdf.set_text_color(*_C["text_dark"])
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 6, desc)

    # -----------------------------------------------------------------------
    # Page 3 — Gap analysis & recommendations
    # -----------------------------------------------------------------------
    pdf.add_page()
    _section_title(pdf, "Svaya Gap Analysis & Recommendations")

    gaps = scores.get("gaps", [])
    recs = scores.get("recommendations", [])

    if not gaps:
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 6, "No significant gaps identified — your network is well-optimised.")
    else:
        for rec in recs:
            pdf.set_fill_color(*_C["bg_light"])
            pdf.rect(pdf.get_x(), pdf.get_y(), 180, 2, "F")
            pdf.ln(3)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*_C["svaya_teal"])
            pdf.cell(0, 6, rec.get("capability", ""), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(*_C["text_dark"])
            pdf.set_font("Helvetica", "", 9)

            domain = rec.get("domain", "")
            current = rec.get("current_score", 0)
            target  = rec.get("target_score", 3)
            pdf.cell(0, 5,
                     f"Domain: {domain}  |  Current: L{current:.1f}  →  Target: L{target}",
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(*_C["text_mid"])
            pdf.multi_cell(0, 5, rec.get("description", ""))
            pdf.set_text_color(*_C["svaya_blue"])
            pdf.set_font("Helvetica", "B", 9)
            pdf.multi_cell(0, 5, f"Expected outcome: {rec.get('outcome', '')}")
            pdf.set_text_color(*_C["text_dark"])
            pdf.ln(4)

    # -----------------------------------------------------------------------
    # Probe results page (if available)
    # -----------------------------------------------------------------------
    if probe_result:
        pdf.add_page()
        _section_title(pdf, "Live Network Readiness Probe Results")

        readiness = probe_result.get("astra_readiness", "")
        summary   = probe_result.get("summary", "")
        r_color   = _READINESS_COLORS.get(readiness, _C["text_mid"])

        pdf.set_fill_color(*r_color)
        pdf.set_text_color(*_C["white"])
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, f"ASTRA Readiness: {readiness}", fill=True,
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(*_C["text_dark"])
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5, summary)
        pdf.ln(4)

        check_keys = ["reachability", "tls_info", "nms_api", "tr369_usp", "pm_sample"]
        for key in check_keys:
            chk = probe_result.get(key, {})
            if not chk:
                continue
            status = chk.get("status", "skip")
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(55, 6, chk.get("check", key))
            _probe_status_dot(pdf, status)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_x(pdf.get_x() + 2)
            pdf.set_text_color(*_C["text_mid"])
            latency = chk.get("latency_ms")
            lat_str = f"  ({latency}ms)" if latency else ""
            pdf.cell(0, 6, chk.get("detail", "")[:90] + lat_str)
            pdf.ln(6)
            pdf.set_text_color(*_C["text_dark"])

    # -----------------------------------------------------------------------
    # Final page — Next steps
    # -----------------------------------------------------------------------
    pdf.add_page()
    _section_title(pdf, "Your Next Steps with Svaya ASTRA")

    steps = [
        ("1", "Book a 30-minute demo",
         "See ASTRA running against a live multi-vendor FWA lab environment. "
         "We'll walk through how ASTRA maps to your specific vendor mix and coverage challenges."),
        ("2", "Request a Proof-of-Value scoping call",
         "Our solutions team will review your gap analysis and propose a 30-day PoV "
         "with defined KPIs — typical targets: ≥15% UL throughput uplift, ≥20% NOC ticket reduction."),
        ("3", "Enable TR-369 USP on your ACS",
         "Svaya's Tier 1 integration requires no on-CPE changes — only TR-369 on your ACS. "
         "We'll provide a step-by-step guide for your vendor."),
        ("4", "Review the TM Forum IG1218 baseline",
         "Our team can run a full TM Forum-aligned autonomy assessment workshop "
         "(half-day, remote) to validate the scores in this report and build a roadmap."),
    ]

    for num, title, body in steps:
        pdf.set_fill_color(*_C["svaya_teal"])
        pdf.set_text_color(*_C["white"])
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(8, 8, num, fill=True, align="C")
        pdf.set_fill_color(*_C["bg_light"])
        pdf.set_text_color(*_C["svaya_blue"])
        pdf.cell(172, 8, f"  {title}", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(*_C["text_dark"])
        pdf.set_font("Helvetica", "", 9)
        pdf.set_x(15)
        pdf.multi_cell(0, 5, body)
        pdf.ln(4)

    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*_C["svaya_blue"])
    pdf.cell(0, 7, "Contact: hello@svaya.io  |  svaya.io/astra  |  +44 20 0000 0000",
             align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    return bytes(pdf.output())


def _text_fallback(
    company: str,
    contact_name: str,
    scores: dict,
    probe_result: Optional[dict],
) -> bytes:
    lines = [
        "SVAYA ASTRA NETWORK AUTONOMY ASSESSMENT",
        f"Company: {company}  |  Contact: {contact_name}",
        f"Overall Maturity: L{scores.get('overall', 0):.1f} — {scores.get('level', '')}",
        "",
        "NOTE: Install fpdf2 to generate a full PDF report.",
        "    pip install fpdf2",
    ]
    return "\n".join(lines).encode()
