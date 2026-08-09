"""Constants for the Daze wallbox integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "daze"

# --- Cognito / OAuth ---
# TODO: find more generic region/user pool ID
COGNITO_REGION = "eu-central-1"
COGNITO_USER_POOL_ID = "eu-central-1_vXrLKLO3t"
COGNITO_CLIENT_ID = "4m0rp7oqarbrc3hn67ivvonba8"

# --- REST backend ---
WEBAPI_BASE_URL = "https://webapi.dazeservice.com"

# --- Config entry data/options keys ---
# CONF_EMAIL/CONF_PASSWORD are homeassistant.const's, reused as-is (not redefined here).
CONF_TOKEN = "token"

DEFAULT_SCAN_INTERVAL = timedelta(seconds=60)
MIN_SCAN_INTERVAL = timedelta(seconds=30)
MAX_SCAN_INTERVAL = timedelta(seconds=300)
CONF_SCAN_INTERVAL = "scan_interval"

# Number of concurrent /remoteInfo requests fired per poll cycle.
MAX_CONCURRENT_SOCKET_REQUESTS = 5

# Cognito access tokens are short-lived (observed: 3600s). Refresh proactively
# this many seconds before expiry rather than waiting for a 401.
TOKEN_REFRESH_LEEWAY_SECONDS = 300

# --- Vendor status enums ---
# `lastStatus` (from /evses) and `evseState` (from /sockets/{serial}/remoteInfo) are the
# same underlying EVSE state enum, cross-referenced against the official web app's
# bundled source (not distributed with this integration - see CLAUDE.md). Keys are the
# integer values observed on the wire; values are translation-key-safe identifiers, with
# the actual display text living in strings.json / translations/*.json.
EVSE_STATE_LABELS: dict[int, str] = {
    0: "unknown",
    1: "standby",
    2: "ev_connected_wait_auth",
    3: "charging",
    4: "evse_error",
    5: "ev_connected_authorized",
    6: "ev_connected_wait_power",
    7: "preparing",
    8: "unavailable",
    9: "finishing",
    10: "reserved",
    100: "scheduled_pause",
    101: "smart_tariff_pause",
}

# `evseSystemError` / `lastEVSESystemError`.
EVSE_SYSTEM_ERROR_LABELS: dict[int, str] = {
    0: "none",
    1: "fault_rcm",
    2: "fault_rcm_test",
    3: "cp_state_e",
    4: "fault_contactor",
    5: "cp_state_invalid",
    6: "overtemperature",
    7: "overcurrent",
    8: "fault_pivot",
    9: "triggered_rcbo",
    10: "evse_not_powered",
    11: "board_l1_overtemp",
}
