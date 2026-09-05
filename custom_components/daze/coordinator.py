"""Data update coordinator for the Daze integration."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DazeApiClient, DazeCannotConnectError
from .const import DOMAIN, MAX_CONCURRENT_SOCKET_REQUESTS
from .models import DazeAccountData, DazeNetworkData

_LOGGER = logging.getLogger(__name__)


class DazeCoordinator(DataUpdateCoordinator[DazeAccountData]):
    def __init__(
        self,
        hass: HomeAssistant,
        api: DazeApiClient,
        email: str,
        identity_id: str,
        update_interval: timedelta,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({email})",
            update_interval=update_interval,
        )
        self._api = api
        self._email = email
        self._identity_id = identity_id

    async def _async_update_data(self) -> DazeAccountData:
        try:
            networks = await self._api.async_get_networks(self._email)
            networks_data: dict[str, DazeNetworkData] = {}
            for network in networks:
                evses = await self._api.async_get_network_evses(network.uid)

                # The network EVSE list contains the normal telemetry, but the
                # current control configuration is exposed by GET /v3/evses/{serial}.
                # Fetch it on every coordinator refresh so the number/select entities
                # are populated immediately at startup and remain in sync with Daze.
                await self._async_fill_evse_details(evses)
                await self._async_fill_socket_remote_info(evses)

                networks_data[network.uid] = DazeNetworkData(
                    network=network, evses=evses
                )
            return DazeAccountData(identity_id=self._identity_id, networks=networks_data)
        except ConfigEntryAuthFailed:
            raise
        except DazeCannotConnectError as err:
            raise UpdateFailed(str(err)) from err

    async def _async_fill_evse_details(self, evses) -> None:
        """Enrich EVSEs with the live control configuration from GET /v3/evses/{serial}."""
        if not evses:
            return
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_SOCKET_REQUESTS)

        async def _fetch(evse) -> None:
            async with semaphore:
                details = await self._api.async_get_evse(evse.serial_number)
                if details is not None:
                    evse.apply_evse_details(details)

        results = await asyncio.gather(
            *(_fetch(evse) for evse in evses), return_exceptions=True
        )
        for result in results:
            if isinstance(result, BaseException):
                raise result

    async def _async_fill_socket_remote_info(self, evses) -> None:
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_SOCKET_REQUESTS)

        async def _fetch(socket) -> None:
            async with semaphore:
                remote_info = await self._api.async_get_socket_remote_info(
                    socket.serial_number
                )
                if remote_info is not None:
                    socket.apply_remote_info(remote_info)

        sockets = [socket for evse in evses for socket in evse.sockets]
        if not sockets:
            return
        results = await asyncio.gather(
            *(_fetch(socket) for socket in sockets), return_exceptions=True
        )
        for result in results:
            if isinstance(result, BaseException):
                raise result

    async def async_set_max_charging_current(
        self, evse_serial: str, milliamps: int
    ) -> None:
        """Set the EVSE maximum external charging current."""
        await self._api.async_set_max_charging_current(evse_serial, milliamps)

    async def async_set_recharge_modality(self, evse_serial: str, mode: int) -> None:
        """Set the EVSE recharge modality."""
        await self._api.async_set_recharge_modality(evse_serial, mode)

    async def async_stop_charge(self, serial_number: str) -> None:
        """Pause the current charging session."""
        await self._api.async_stop_charge(serial_number)

    async def async_play_charge(self, serial_number: str) -> None:
        """Resume the current charging session."""
        await self._api.async_play_charge(serial_number)
