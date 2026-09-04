"""Select entities for Daze EVSE controls."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import RECHARGE_MODALITY_SELFCONSUMPTION, RECHARGE_MODALITY_STANDARD
from .const import DOMAIN
from .entity import DazeEvseEntity, evse_device_info
from .models import DazeEvse

MODE_STANDARD = "Standard"
MODE_AUTO = "Auto"
MODE_OPTIONS = [MODE_STANDARD, MODE_AUTO]
MODE_TO_API = {MODE_STANDARD: RECHARGE_MODALITY_STANDARD, MODE_AUTO: RECHARGE_MODALITY_SELFCONSUMPTION}
API_TO_MODE = {value: key for key, value in MODE_TO_API.items()}


def _primary_socket(evse: DazeEvse):
    return next(
        (socket for socket in evse.sockets if socket.is_primary),
        evse.sockets[0] if evse.sockets else None,
    )


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        DazeChargingModeSelect(coordinator, network_uid, evse.serial_number)
        for network_uid, network_data in coordinator.data.networks.items()
        for evse in network_data.evses
    ]
    async_add_entities(entities)


class DazeChargingModeSelect(DazeEvseEntity, SelectEntity):
    """Select and display the live Daze recharge modality."""

    _attr_translation_key = "charging_mode"
    _attr_options = MODE_OPTIONS

    def __init__(self, coordinator, network_uid: str, evse_serial: str) -> None:
        super().__init__(coordinator, network_uid, evse_serial)
        self._attr_unique_id = f"{evse_serial}_charging_mode"
        evse = self._evse
        if evse is not None:
            self._attr_device_info = evse_device_info(self._network_data.network, evse)

    @property
    def current_option(self) -> str | None:
        evse = self._evse
        if evse is None:
            return None
        socket = _primary_socket(evse)
        if socket is None:
            return None
        # operation_mode is populated from the live remoteInfo response when
        # the coordinator starts and on every subsequent coordinator refresh.
        return API_TO_MODE.get(socket.operation_mode)

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_recharge_modality(
            self._evse_serial, MODE_TO_API[option]
        )
        await self.coordinator.async_request_refresh()
