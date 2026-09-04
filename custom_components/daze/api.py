"""REST client for the Daze backend (webapi.dazeservice.com)."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

import aiohttp
from homeassistant.exceptions import ConfigEntryAuthFailed

from .auth import DazeAuth
from .const import REQUEST_TIMEOUT, REQUEST_TIMEOUT_RETRIES, WEBAPI_BASE_URL
from .exceptions import DazeAuthError, DazeCannotConnectError
from .models import DazeEvse, DazeNetwork

_LOGGER = logging.getLogger(__name__)

# Daze API rechargeModality values used when writing to the backend.
# IMPORTANT: the GET /v3/evses/{serial} response uses a different zero-based
# representation in network.rechargeModality:
#   GET 0 = Standard, 1 = Auto / self-consumption
#   PUT 1 = Standard, 2 = Auto / self-consumption
RECHARGE_MODALITY_STANDARD = 1
RECHARGE_MODALITY_SELFCONSUMPTION = 2


class DazeApiClient:
    def __init__(self, session: aiohttp.ClientSession, auth: DazeAuth) -> None:
        self._session = session
        self._auth = auth

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Perform one authenticated REST call with auth and timeout retries."""
        url = f"{WEBAPI_BASE_URL}{path}"
        refreshed = False
        retries_left = REQUEST_TIMEOUT_RETRIES
        while True:
            try:
                token = await self._auth.async_get_access_token()
            except DazeAuthError as err:
                raise ConfigEntryAuthFailed(str(err)) from err

            try:
                async with self._session.request(
                    method,
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=REQUEST_TIMEOUT,
                    **kwargs,
                ) as resp:
                    if resp.status == 401:
                        if refreshed:
                            raise ConfigEntryAuthFailed(
                                f"Backend rejected refreshed token for {path}"
                            )
                        _LOGGER.debug("401 from %s, forcing token refresh and retrying once", path)
                        try:
                            await self._auth.async_refresh()
                        except DazeAuthError as err:
                            raise ConfigEntryAuthFailed(str(err)) from err
                        refreshed = True
                        continue
                    if resp.status == 404:
                        return None
                    if resp.status >= 400:
                        text = await resp.text()
                        raise DazeCannotConnectError(
                            f"{method} {path} -> HTTP {resp.status}: {text[:300]}"
                        )
                    if resp.content_length == 0:
                        return None
                    payload = await resp.json()
                    return payload.get("data")
            except TimeoutError as err:
                if retries_left:
                    retries_left -= 1
                    _LOGGER.debug(
                        "Timeout on %s %s, retrying (%d left)", method, path, retries_left
                    )
                    continue
                raise DazeCannotConnectError(
                    f"{method} {path} timed out after {REQUEST_TIMEOUT.total}s"
                ) from err
            except aiohttp.ClientError as err:
                raise DazeCannotConnectError(f"{method} {path}: {err}") from err

    async def async_get_user_profile(self, email: str) -> dict[str, Any]:
        return await self._request("GET", f"/v3/users/{quote(email)}/", params={"appName": 1})

    async def async_get_networks(self, email: str) -> list[DazeNetwork]:
        raw_list = await self._request(
            "GET", f"/v3/users/{quote(email)}/networks", params={"includeStats": "true"}
        )
        return [DazeNetwork.from_dict(raw) for raw in (raw_list or [])]

    async def async_get_network_evses(self, network_uid: str) -> list[DazeEvse]:
        raw_list = await self._request(
            "GET", f"/v3/networks/{network_uid}/evses", params={"includeEcoInfo": "false"}
        )
        return [DazeEvse.from_dict(raw) for raw in (raw_list or [])]

    async def async_get_socket_remote_info(self, serial_number: str) -> dict[str, Any] | None:
        return await self._request(
            "GET",
            f"/v3/sockets/{serial_number}/remoteInfo",
            params={"includeEcoInfo": "true", "includeNextSchedule": "true"},
        )

    async def async_get_evse(self, evse_serial: str) -> dict[str, Any] | None:
        """Fetch a single EVSE (includes rechargeModality)."""
        return await self._request("GET", f"/v3/evses/{evse_serial}")

    async def async_set_recharge_modality(self, evse_serial: str, mode: int) -> None:
        """Set the Daze recharge modality: 1=standard, 2=self-consumption."""
        await self._request(
            "PUT",
            f"/v3/evses/{evse_serial}/rechargeModality",
            json={"newRechargeModality": mode, "sendRpcToDevice": True},
        )

    async def async_set_max_charging_current(self, evse_serial: str, milliamps: int) -> None:
        """Set maximum external charging current in milliamps."""
        await self._request(
            "POST",
            f"/v3/evses/{evse_serial}/configurations/maxExternalChargingCurrent",
            json={
                "evseSerialNumber": evse_serial,
                "maxExternalChargingCurrentInMilliAmps": milliamps,
            },
        )
