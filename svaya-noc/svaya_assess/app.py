"""
Svaya ASTRA Assessment Tool — Flask application.
Standalone marketing tool: TM Forum L0-L4 survey + optional live network probe.
"""

import json
import os
import sys

from flask import (
    Flask,
    abort,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)

sys.path.insert(0, os.path.dirname(__file__))

from lead_store import get_lead, save_lead
from network_probe import probe_to_dict, run_probe
from report_gen import generate_pdf
from survey_engine import (
    BENCHMARKS,
    DOMAIN_LABELS,
    LEVEL_COLORS,
    LEVEL_LABELS,
    SECTIONS,
    SVAYA_CAPABILITIES,
    MaturityScore,
    bar_pct,
    benchmark_pct,
    score_answers,
)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.getenv("FLASK_SECRET", "svaya-assess-dev-secret")


# ---------------------------------------------------------------------------
# Landing page
# ---------------------------------------------------------------------------

@app.route("/")
def landing():
    return render_template("landing.html")


# ---------------------------------------------------------------------------
# Survey
# ---------------------------------------------------------------------------

@app.route("/survey")
def survey():
    return render_template("survey.html", sections=SECTIONS)


@app.route("/survey/submit", methods=["POST"])
def survey_submit():
    form = request.form

    # Contact fields
    company      = (form.get("company") or "").strip()
    contact_name = (form.get("contact_name") or "").strip()
    email        = (form.get("email") or "").strip()
    phone        = (form.get("phone") or "").strip()
    country      = (form.get("country") or "").strip()
    network_size = (form.get("network_size") or "").strip()

    if not company or not contact_name or not email:
        return render_template(
            "survey.html",
            sections=SECTIONS,
            error="Please fill in company, name, and email.",
        ), 400

    # Gather survey answers — form keys have "q_" prefix to avoid collisions with
    # top-level contact fields; strip the prefix before passing to score_answers.
    answers = {}
    for key, val in form.items():
        if key.startswith("q_"):
            qid = key[2:]  # strip "q_" prefix → matches survey_engine question ids
            try:
                answers[qid] = int(val)
            except (ValueError, TypeError):
                answers[qid] = val

    maturity: MaturityScore = score_answers(answers)
    scores_dict = {
        "domains":         maturity.domains,
        "overall":         maturity.overall,
        "level":           maturity.level,
        "gaps":            maturity.gaps,
        "recommendations": maturity.recommendations,
    }

    # Optional network probe
    probe_result = None
    run_probe_flag = form.get("run_probe") == "yes"
    if run_probe_flag:
        nms_endpoint = (form.get("nms_endpoint") or "").strip()
        nms_vendor   = (form.get("nms_vendor") or "generic").strip()
        pm_user      = (form.get("pm_username") or "").strip()
        pm_pass      = (form.get("pm_password") or "").strip()
        if nms_endpoint:
            try:
                report = run_probe(nms_endpoint, nms_vendor, pm_user, pm_pass)
                probe_result = probe_to_dict(report)
            except Exception as exc:
                probe_result = {"error": str(exc), "astra_readiness": "UNREACHABLE"}

    lead_id = save_lead(
        company=company,
        contact_name=contact_name,
        email=email,
        phone=phone,
        country=country,
        network_size=network_size,
        answers=answers,
        scores=scores_dict,
        probe_result=probe_result,
    )

    return redirect(url_for("results", lead_id=lead_id))


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

@app.route("/results/<lead_id>")
def results(lead_id: str):
    lead = get_lead(lead_id)
    if not lead:
        abort(404)

    scores = lead.scores
    probe  = lead.probe_result

    # Build benchmark comparison data for template
    domain_rows = []
    for domain, label in DOMAIN_LABELS.items():
        score = scores.get("domains", {}).get(domain, 0)
        bench_avg = BENCHMARKS.get(domain, {}).get("avg", 1.2)
        bench_top = BENCHMARKS.get(domain, {}).get("top_quartile", 2.8)
        domain_rows.append({
            "domain":    domain,
            "label":     label,
            "score":     score,
            "pct":       bar_pct(score),
            "bench_pct": benchmark_pct(domain, "avg"),
            "bench_avg": bench_avg,
            "bench_top": bench_top,
            "level_color": LEVEL_COLORS.get(int(round(score)), "#888"),
        })

    return render_template(
        "results.html",
        lead=lead,
        scores=scores,
        domain_rows=domain_rows,
        level_label=scores.get("level", ""),
        level_color=LEVEL_COLORS.get(int(round(scores.get("overall", 0))), "#888"),
        probe=probe,
        recommendations=scores.get("recommendations", []),
    )


# ---------------------------------------------------------------------------
# PDF download
# ---------------------------------------------------------------------------

@app.route("/results/<lead_id>/pdf")
def download_pdf(lead_id: str):
    lead = get_lead(lead_id)
    if not lead:
        abort(404)

    pdf_bytes = generate_pdf(
        company=lead.company,
        contact_name=lead.contact_name,
        email=lead.email,
        scores=lead.scores,
        probe_result=lead.probe_result,
        lead_id=lead_id,
    )

    resp = make_response(pdf_bytes)
    resp.headers["Content-Type"] = "application/pdf"
    safe_company = "".join(c if c.isalnum() else "_" for c in lead.company)
    resp.headers["Content-Disposition"] = (
        f'attachment; filename="Svaya_Assessment_{safe_company}.pdf"'
    )
    return resp


# ---------------------------------------------------------------------------
# Live probe API (AJAX, consent-gated)
# ---------------------------------------------------------------------------

@app.route("/probe", methods=["POST"])
def live_probe():
    """Standalone probe endpoint — called via AJAX from survey form when operator opts in."""
    data = request.get_json(silent=True) or {}
    endpoint = (data.get("endpoint") or "").strip()
    vendor   = (data.get("vendor") or "generic").strip()
    pm_user  = (data.get("pm_username") or "").strip()
    pm_pass  = (data.get("pm_password") or "").strip()

    if not endpoint:
        return {"error": "endpoint is required"}, 400

    try:
        report = run_probe(endpoint, vendor, pm_user, pm_pass)
        return probe_to_dict(report)
    except Exception as exc:
        return {"error": str(exc), "astra_readiness": "UNREACHABLE"}, 500


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.route("/health")
def health():
    return {"status": "ok", "service": "svaya-assess"}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.getenv("ASSESS_PORT", 5050))
    debug = os.getenv("FLASK_ENV", "production") == "development"
    print(f"Svaya Assessment Tool running on http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
