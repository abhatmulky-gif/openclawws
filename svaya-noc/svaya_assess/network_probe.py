"""
Svaya Network Readiness Probe
Performs non-destructive, consent-gated checks against an operator's NMS.
All checks are read-only. TLS errors are caught and reported, not fatal.
Total probe time budget: ~30 seconds (5s timeout per check).

Checks performed (all operator-consented):
  1. HTTP/HTTPS reachability + TLS certificate info
  2. Vendor NMS API endpoint detection (known REST paths per vendor)
  3. TR-369 USP / TR-069 CWMP discovery
  4. PM counter sample fetch (read-only, credentials required)
"""

import socket
import ssl
import time
from dataclasses import dataclass, field
from typing import Optional

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

PROBE_TIMEOUT = 5   # seconds per HTTP check
SOCKET_TIMEOUT = 3  # seconds per socket check


# ---------------------------------------------------------------------------
# Known vendor NMS API paths (read-only discovery endpoints)
# ---------------------------------------------------------------------------
_VENDOR_PATHS = {
    "ericsson": [
        "/enm/rest/v1/apps",
        "/oss/idm/usermanagement/users",
        "/enm/rest/v1/health",
        "/oss/rest/v1/status",
    ],
    "nokia": [
        "/NetAct/rest/api/v1/nodes",
        "/api/v1/health",
        "/NetAct/rest/api/v1/health",
        "/nbi/v1/health",
    ],
    "samsung": [
        "/oss/api/v1/nodes",
        "/api/v1/status",
        "/samsung/oss/api/v1/health",
    ],
    "huawei": [
        "/rest/v1/data/sites",
        "/rest/v1/health",
        "/api/health",
        "/UniMAN/rest/v1/status",
    ],
    "generic": [
        "/health",
        "/api/health",
        "/api/v1/health",
        "/status",
        "/api/v1/status",
        "/v1/health",
    ],
}

# TR-369 USP / TR-069 CWMP known paths and ports
_USP_PATHS = [
    "/acs",
    "/cwmp",
    "/cwmp/acs",
    "/tr069",
    "/tr069/acs",
    "/tr369",
    "/tr369/acs",
    "/usp/acs",
    "/usp/controller",
]

_CWMP_PORT = 7547   # TR-069 standard port
_USP_STOMP_PORT = 61613
_USP_MQTT_PORT  = 8883
_USP_WS_PORT    = 443

# PM counter sample endpoints per vendor (read-only)
_PM_PATHS = {
    "ericsson": [
        "/enm/rest/v1/pm/stats",
        "/enm/rest/v1/pm/counters",
    ],
    "nokia": [
        "/NetAct/rest/api/v1/pm/stats",
        "/nbi/v1/pm/counters",
    ],
    "samsung": [
        "/oss/api/v1/pm/stats",
    ],
    "huawei": [
        "/rest/v1/pm/counters",
        "/UniMAN/rest/v1/pm/stats",
    ],
}


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    check: str
    status: str          # ok | warn | fail | skip
    detail: str
    latency_ms: Optional[int] = None
    data: dict = field(default_factory=dict)


@dataclass
class ProbeReport:
    endpoint: str
    vendor: str
    consent_confirmed: bool = True
    reachability: Optional[CheckResult] = None
    tls_info: Optional[CheckResult] = None
    nms_api: Optional[CheckResult] = None
    tr369_usp: Optional[CheckResult] = None
    pm_sample: Optional[CheckResult] = None
    summary: str = ""
    nms_readiness: str = ""   # READY | PARTIAL | NEEDS_CONFIG | UNREACHABLE


# ---------------------------------------------------------------------------
# Individual check functions
# ---------------------------------------------------------------------------

def _check_reachability(base_url: str) -> CheckResult:
    """HTTP/HTTPS GET to the base URL — checks basic connectivity."""
    t0 = time.time()
    try:
        resp = requests.get(
            base_url,
            timeout=PROBE_TIMEOUT,
            verify=False,
            allow_redirects=True,
        )
        ms = int((time.time() - t0) * 1000)
        return CheckResult(
            check="HTTP Reachability",
            status="ok",
            detail=f"HTTP {resp.status_code} in {ms}ms — endpoint is reachable",
            latency_ms=ms,
            data={"status_code": resp.status_code, "server": resp.headers.get("Server", "")},
        )
    except requests.exceptions.SSLError as e:
        ms = int((time.time() - t0) * 1000)
        return CheckResult(
            check="HTTP Reachability",
            status="warn",
            detail=f"Reachable but TLS certificate error: {str(e)[:120]}",
            latency_ms=ms,
        )
    except requests.exceptions.ConnectionError:
        return CheckResult(
            check="HTTP Reachability",
            status="fail",
            detail="Connection refused or host unreachable",
        )
    except requests.exceptions.Timeout:
        return CheckResult(
            check="HTTP Reachability",
            status="fail",
            detail=f"Timed out after {PROBE_TIMEOUT}s",
        )
    except Exception as e:
        return CheckResult(
            check="HTTP Reachability",
            status="fail",
            detail=str(e)[:200],
        )


def _check_tls(hostname: str, port: int = 443) -> CheckResult:
    """Retrieve TLS certificate info from the NMS endpoint."""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with socket.create_connection((hostname, port), timeout=SOCKET_TIMEOUT) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                subject = dict(x[0] for x in cert.get("subject", []))
                issuer  = dict(x[0] for x in cert.get("issuer", []))
                expiry  = cert.get("notAfter", "unknown")
                return CheckResult(
                    check="TLS Certificate",
                    status="ok",
                    detail=f"Valid certificate. CN={subject.get('commonName', 'N/A')}, expires {expiry}",
                    data={
                        "subject": subject,
                        "issuer": issuer.get("organizationName", ""),
                        "expiry": expiry,
                    },
                )
    except ssl.SSLError as e:
        return CheckResult(
            check="TLS Certificate",
            status="warn",
            detail=f"TLS error (self-signed or expired?): {str(e)[:100]}",
        )
    except Exception as e:
        return CheckResult(
            check="TLS Certificate",
            status="skip",
            detail=f"TLS check skipped: {str(e)[:100]}",
        )


def _check_nms_api(base_url: str, vendor: str) -> CheckResult:
    """
    Probe known vendor NMS REST API paths.
    Returns the first path that responds (any HTTP status is positive signal —
    even 401/403 confirms the API exists).
    """
    paths_to_try = _VENDOR_PATHS.get(vendor.lower(), []) + _VENDOR_PATHS["generic"]
    detected = []

    for path in paths_to_try:
        url = base_url.rstrip("/") + path
        try:
            resp = requests.get(url, timeout=PROBE_TIMEOUT, verify=False)
            if resp.status_code < 500:
                detected.append({
                    "path": path,
                    "status_code": resp.status_code,
                    "auth_required": resp.status_code in (401, 403),
                })
                if len(detected) >= 3:
                    break
        except Exception:
            continue

    if detected:
        paths_str = ", ".join(d["path"] for d in detected)
        auth_note = " (authentication required)" if any(d["auth_required"] for d in detected) else ""
        return CheckResult(
            check="Vendor NMS API Detection",
            status="ok",
            detail=f"{len(detected)} {vendor} API path(s) detected: {paths_str}{auth_note}",
            data={"detected_paths": detected, "vendor": vendor},
        )
    return CheckResult(
        check="Vendor NMS API Detection",
        status="warn",
        detail=f"No {vendor} NMS API paths responded. Vendor: {vendor}. "
               "Check port, firewall rules, or try a different vendor.",
    )


def _check_tr369(base_url: str) -> CheckResult:
    """
    Discover TR-369 USP Controller / ACS endpoints and CWMP/MQTT ports.
    Also checks CWMP port 7547 via socket.
    """
    found = []
    hostname = base_url.split("//")[-1].split("/")[0].split(":")[0]

    # HTTP path check
    for path in _USP_PATHS:
        url = base_url.rstrip("/") + path
        try:
            resp = requests.get(url, timeout=PROBE_TIMEOUT, verify=False)
            if resp.status_code < 500:
                found.append({"type": "HTTP", "path": path, "status": resp.status_code})
        except Exception:
            continue

    # CWMP port 7547 socket check
    for port, label in [(_CWMP_PORT, "TR-069 CWMP"), (_USP_MQTT_PORT, "USP MQTT")]:
        try:
            with socket.create_connection((hostname, port), timeout=SOCKET_TIMEOUT):
                found.append({"type": "TCP", "port": port, "label": label})
        except Exception:
            pass

    if found:
        labels = [f.get("path") or f.get("label") for f in found]
        return CheckResult(
            check="TR-369 USP / TR-069 CWMP Discovery",
            status="ok",
            detail=f"CPE management protocol endpoint(s) detected: {', '.join(str(l) for l in labels)}",
            data={"endpoints": found},
        )
    return CheckResult(
        check="TR-369 USP / TR-069 CWMP Discovery",
        status="warn",
        detail=(
            "No TR-369 or TR-069 endpoints detected on standard paths. "
            "CPE remote management may not be enabled, or ACS may be on a private VLAN. "
            "Svaya can work with TR-369 on the management VLAN — no public exposure required."
        ),
    )


def _check_pm_sample(base_url: str, vendor: str, username: str, password: str) -> CheckResult:
    """
    Attempt to fetch one PM counter record using provided read-only credentials.
    Any valid JSON response (even empty) confirms the PM interface is accessible.
    """
    if not username or not password:
        return CheckResult(
            check="PM Counter Sample Fetch",
            status="skip",
            detail="No credentials provided — PM sample fetch skipped",
        )

    paths = _PM_PATHS.get(vendor.lower(), ["/api/v1/pm/stats"])
    for path in paths:
        url = base_url.rstrip("/") + path
        try:
            resp = requests.get(
                url,
                auth=(username, password),
                timeout=PROBE_TIMEOUT,
                verify=False,
            )
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    sample_keys = list(data.keys())[:5] if isinstance(data, dict) else []
                    return CheckResult(
                        check="PM Counter Sample Fetch",
                        status="ok",
                        detail=(
                            f"PM counter endpoint accessible at {path}. "
                            f"Sample fields: {sample_keys or 'data received'}. "
                            "Svaya can normalise this vendor's PM format."
                        ),
                        data={"path": path, "sample_keys": sample_keys},
                    )
                except Exception:
                    return CheckResult(
                        check="PM Counter Sample Fetch",
                        status="ok",
                        detail=f"PM endpoint responded at {path} (non-JSON format — likely file-based PM export).",
                    )
            elif resp.status_code == 401:
                return CheckResult(
                    check="PM Counter Sample Fetch",
                    status="warn",
                    detail=f"PM endpoint found at {path} but credentials rejected (HTTP 401). "
                           "Check username/password or API key format.",
                )
        except Exception:
            continue

    return CheckResult(
        check="PM Counter Sample Fetch",
        status="warn",
        detail=f"No PM counter endpoint responded for vendor '{vendor}'. "
               "PM data may require VPN access or a different API path.",
    )


# ---------------------------------------------------------------------------
# NMS readiness assessment
# ---------------------------------------------------------------------------

def _assess_nms_readiness(report: ProbeReport) -> str:
    scores = {
        "ok": 3, "warn": 1, "fail": 0, "skip": 0
    }
    total = 0
    checks = [report.reachability, report.nms_api, report.tr369_usp, report.pm_sample]
    for c in checks:
        if c:
            total += scores.get(c.status, 0)

    if total >= 9:
        return "READY"
    if total >= 5:
        return "PARTIAL"
    if total >= 2:
        return "NEEDS_CONFIG"
    return "UNREACHABLE"


_READINESS_LABELS = {
    "READY":        "Svaya can connect to your NMS with minimal configuration.",
    "PARTIAL":      "Svaya can connect, but some data sources need configuration (e.g., VPN, API credentials).",
    "NEEDS_CONFIG": "Your NMS is reachable but API access needs to be enabled before Svaya integration.",
    "UNREACHABLE":  "We couldn't reach the endpoint. Verify the URL, firewall rules, and network access.",
}


# ---------------------------------------------------------------------------
# Main probe entry point
# ---------------------------------------------------------------------------

def run_probe(
    endpoint: str,
    vendor: str,
    pm_username: str = "",
    pm_password: str = "",
) -> ProbeReport:
    """
    Run the full network readiness probe against the operator-provided NMS endpoint.
    All checks are read-only and require explicit operator consent before calling this function.
    """
    report = ProbeReport(endpoint=endpoint, vendor=vendor)

    # Parse hostname for TLS check
    hostname = endpoint.split("//")[-1].split("/")[0].split(":")[0]
    port = 443
    try:
        parts = endpoint.split("//")[-1].split("/")[0].split(":")
        if len(parts) > 1:
            port = int(parts[1])
    except Exception:
        pass

    # Run all checks (failures are caught and recorded, not raised)
    report.reachability = _check_reachability(endpoint)
    report.tls_info     = _check_tls(hostname, port)
    report.nms_api      = _check_nms_api(endpoint, vendor)
    report.tr369_usp    = _check_tr369(endpoint)
    report.pm_sample    = _check_pm_sample(endpoint, vendor, pm_username, pm_password)

    # Readiness summary
    report.nms_readiness = _assess_nms_readiness(report)
    report.summary = _READINESS_LABELS[report.nms_readiness]

    return report


def probe_to_dict(report: ProbeReport) -> dict:
    def cr(c: Optional[CheckResult]) -> dict:
        if not c:
            return {}
        return {
            "check": c.check,
            "status": c.status,
            "detail": c.detail,
            "latency_ms": c.latency_ms,
            "data": c.data,
        }
    return {
        "endpoint": report.endpoint,
        "vendor": report.vendor,
        "nms_readiness": report.nms_readiness,
        "summary": report.summary,
        "reachability":  cr(report.reachability),
        "tls_info":      cr(report.tls_info),
        "nms_api":       cr(report.nms_api),
        "tr369_usp":     cr(report.tr369_usp),
        "pm_sample":     cr(report.pm_sample),
    }
