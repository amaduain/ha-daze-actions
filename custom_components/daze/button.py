"""Button entities for Daze EVSE charging-session actions."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import DazeEvseEntity, evse_device_info


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        DazeChargingActionButton(coordinator, network_uid, evse.serial_number, action)
        for network_uid, network_data in coordinator.data.networks.items()
        for evse in network_data.evses
        for action in ("pause", "resume")
    ]
    async_add_entities(entities)


class DazeChargingActionButton(DazeEvseEntity, ButtonEntity):
    """Execute a charging-session action on a Daze EVSE."""

    def __init__(self, coordinator, network_uid: str, evse_serial: str, action: str) -> None:
        super().__init__(coordinator, network_uid, evse_serial)
        self._action = action
        self._attr_unique_id = f"{evse_serial}_{action}_charging"
        self._attr_translation_key = action

        evse = self._evse
        if evse is not None:
            self._attr_device_info = evse_device_info(self._network_data.network, evse)

    async def async_press(self) -> None:
        if self._action == "pause":
            await self.coordinator.async_stop_charge(self._evse_serial)
        else:
            await self.coordinator.async_play_charge(self._evse_serial)

        # Refresh immediately so status/telemetry reflects the command.
        await self.coordinator.async_request_refresh()
