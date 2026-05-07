"""
Network Probe skill — wraps network_probe.py as a conversational assessment.
Collects endpoint, vendor, optional credentials through the chat UI,
runs the live probe, and returns results in-conversation.
"""

from .base import BaseSkill, SubScenario, Criterion, CriterionOption

_O = CriterionOption


class NetworkProbeSkill(BaseSkill):

    id          = "network_probe"
    name        = "Live Network Readiness Probe"
    description = (
        "Performs five non-destructive read-only checks against your NMS "
        "and reports ASTRA readiness. Requires your NMS endpoint URL and "
        "optional PM API credentials. No changes are made to your network."
    )
    icon = "🔍"

    # Network probe is not a scored L0-L5 assessment — it has a single
    # scenario and uses custom flow (handled by orchestrator directly).
    scenarios = [
        SubScenario(
            id="probe",
            name="Live Probe",
            description="Read-only checks against your NMS",
            weight=1.0,
        )
    ]

    # Criteria here collect the inputs needed to run the probe
    criteria = [
        Criterion(
            id="probe_consent",
            name="Consent",
            cognitive_activity="Execution",
            weight=1.0,
            scenario_specific=False,
            question=(
                "This skill will perform five read-only network checks:\n"
                "1. HTTP/HTTPS reachability\n"
                "2. TLS certificate information\n"
                "3. Vendor NMS REST API detection\n"
                "4. TR-369 USP / TR-069 CWMP discovery\n"
                "5. PM counter sample fetch (optional, needs credentials)\n\n"
                "**No changes will be made to your network.** "
                "Do you consent to these checks?"
            ),
            options=[
                _O(1, "Yes, I consent",  "Proceed with read-only checks", ["yes", "consent", "proceed"]),
                _O(0, "No, skip probe",  "Skip the live probe",            ["no", "skip", "cancel"]),
            ],
        ),
    ]

    # Probe inputs are collected as free-text by the orchestrator after consent.
    PROBE_INPUTS = ["nms_endpoint", "nms_vendor", "pm_username", "pm_password"]

    def get_intro_message(self) -> str:
        return (
            "## Live Network Readiness Probe\n\n"
            "ASTRA will perform five read-only checks against your NMS endpoint. "
            "This takes approximately 30 seconds. No configuration changes are made.\n\n"
            "You will need:\n"
            "- Your NMS base URL (e.g., `https://nms.yournetwork.com`)\n"
            "- Your RAN vendor (Ericsson, Nokia, Samsung, Huawei, or generic)\n"
            "- Optional: a read-only PM API username and password\n\n"
            "Let's begin."
        )


skill = NetworkProbeSkill()
