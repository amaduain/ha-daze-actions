"""Number entities for Daze EVSE controls."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import DazeEvseEntity, evse_device_info
from .models import DazeEvse

MIN_CHARGING_POWER_KW = 1.4
MAX_CHARGING_POWER_KW_SINGLE_PHASE = 7.4
MAX_CHARGING_POWER_KW_THREE_PHASE = 22.0
CHARGING_POWER_STEP_KW = 0.1


def _primary_socket(evse: DazeEvse):
    return next(
        (socket for socket in evse.sockets if socket.is_primary),
        evse.sockets[0] if evse.sockets else None,
    )


def _ma_to_kw(milliamps: int | None) -> float | None:
    if milliamps is None:
        return None
    return (milliamps / 1000) * 230 / 1000


def _kw_to_ma(power_kw: float) -> int:
    amps = (power_kw * 1000) / 230
    return round(amps * 1000)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        DazeChargingPowerNumber(coordinator, network_uid, evse.serial_number)
        for network_uid, network_data in coordinator.data.networks.items()
        for evse in network_data.evses
    ]
    async_add_entities(entities)


class DazeChargingPowerNumber(DazeEvseEntity, NumberEntity):
    """Set the maximum external charging power of an EVSE."""

    _attr_translation_key = "charging_power"
    _attr_device_class = NumberDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_native_min_value = MIN_CHARGING_POWER_KW
    _attr_native_step = CHARGING_POWER_STEP_KW
    _attr_mode = "slider"

    def __init__(self, coordinator, network_uid: str, evse_serial: str) -> None:
        super().__init__(coordinator, network_uid, evse_serial)
        self._attr_unique_id = f"{evse_serial}_charging_power"
        evse = self._evse
        if evse is not None:
            self._attr_device_info = evse_device_info(self._network_data.network, evse)
            self._attr_native_max_value = (
                MAX_CHARGING_POWER_KW_THREE_PHASE
                if evse.evse_is_three_phase
                else MAX_CHARGING_POWER_KW_SINGLE_PHASE
            )

    @property
    def native_value(self) -> float | None:
        evse = self._evse
        if evse is None:
            return None
        socket = _primary_socket(evse)
        return _ma_to_kw(socket.last_max_charging_current) if socket is not None else None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_max_charging_current(
            self._evse_serial, _kw_to_ma(value)
        )
        await self.coordinator.async_request_refresh()
