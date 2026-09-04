"""Lightweight data models for the Daze backend.

These mirror the shape of the (undocumented, reverse-engineered) REST responses from
webapi.dazeservice.com just closely enough to serve the v1 sensor set. Unknown/unused
fields in the raw payloads are simply ignored rather than modeled - do not try to
capture every field the vendor's app happens to use internally.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DazeCurrency:
    code: str | None
    symbol: str | None

    @classmethod
    def from_dict(cls, raw: dict | None) -> DazeCurrency:
        raw = raw or {}
        return cls(code=raw.get("code"), symbol=raw.get("symbol"))


@dataclass
class DazeNetwork:
    uid: str
    name: str | None
    address: str | None
    city: str | None
    country: str | None
    time_zone: str | None
    currency: DazeCurrency
    energy_cost: float | None
    price_energy: float | None
    is_photovoltaic: bool
    grid_is_three_phase: bool
    supply_max_power: int | None
    num_evses_in_network: int | None

    @classmethod
    def from_dict(cls, raw: dict) -> DazeNetwork:
        return cls(
            uid=raw["uid"], name=raw.get("name"), address=raw.get("address"),
            city=raw.get("city"), country=raw.get("country"),
            time_zone=raw.get("timeZone"), currency=DazeCurrency.from_dict(raw.get("currency")),
            energy_cost=raw.get("energyCost"), price_energy=raw.get("priceEnergy"),
            is_photovoltaic=bool(raw.get("isPhotovoltaic", False)),
            grid_is_three_phase=bool(raw.get("gridIsThreePhase", False)),
            supply_max_power=raw.get("supplyMaxPower"),
            num_evses_in_network=raw.get("numEvsesInNetwork"),
        )


@dataclass
class DazeSocket:
    id: str
    serial_number: str
    is_primary: bool
    last_status: int | None
    operation_mode: int | None
    last_power: int | None
    last_energy: int | None
    last_max_charging_current: int | None
    last_charging_current_l1: int | None
    last_charging_current_l2: int | None
    last_charging_current_l3: int | None
    last_ac_voltage_l1: int | None
    last_ac_voltage_l2: int | None
    last_ac_voltage_l3: int | None
    last_board_temperature: int | None
    last_case_temperature: int | None
    last_fan_status: int | None
    last_session_id: int | None
    last_attributes_updated_on: str | None
    evse_state: int | None = None
    evse_suspension_reason: int | None = None
    evse_system_error: int | None = None
    is_paused: bool | None = None
    active: bool | None = None
    remote_max_charging_current: int | None = None
    remote_recharge_modality: int | None = None

    @classmethod
    def from_dict(cls, raw: dict) -> DazeSocket:
        return cls(
            id=raw["id"], serial_number=raw["serialNumber"],
            is_primary=bool(raw.get("isPrimary", False)), last_status=raw.get("lastStatus"),
            operation_mode=raw.get("operationMode"), last_power=raw.get("lastPower"),
            last_energy=raw.get("lastEnergy"), last_max_charging_current=raw.get("lastMaxChargingCurrent"),
            last_charging_current_l1=raw.get("lastChargingCurrentInstantL1"),
            last_charging_current_l2=raw.get("lastChargingCurrentInstantL2"),
            last_charging_current_l3=raw.get("lastChargingCurrentInstantL3"),
            last_ac_voltage_l1=raw.get("lastACVoltageL1"), last_ac_voltage_l2=raw.get("lastACVoltageL2"),
            last_ac_voltage_l3=raw.get("lastACVoltageL3"), last_board_temperature=raw.get("lastBoardL1Temperature"),
            last_case_temperature=raw.get("lastCaseTemperature"), last_fan_status=raw.get("lastFanStatus"),
            last_session_id=raw.get("lastSessionId"), last_attributes_updated_on=raw.get("lastAttributesUpdatedOn"),
        )

    def apply_remote_info(self, raw: dict) -> None:
        """Merge live state returned by GET /v3/sockets/{serial}/remoteInfo."""
        self.evse_state = raw.get("evseState")
        self.evse_suspension_reason = raw.get("evseSuspensionReason")
        self.evse_system_error = raw.get("evseSystemError")
        self.is_paused = raw.get("isPaused")
        self.active = raw.get("active")

        self.remote_max_charging_current = _first_int(
            raw,
            "maxExternalChargingCurrentInMilliAmps",
            "maxChargingCurrentInMilliAmps",
            "maxExternalChargingCurrent",
            "maxChargingCurrent",
        )
        self.remote_recharge_modality = _first_int(
            raw, "rechargeModality", "currentRechargeModality"
        )

        if self.remote_max_charging_current is not None:
            self.last_max_charging_current = self.remote_max_charging_current


def _first_int(raw: dict, *keys: str) -> int | None:
    for key in keys:
        value = raw.get(key)
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                pass
    return None


@dataclass
class DazeEvse:
    serial_number: str
    evse_name: str | None
    device_profile: str | None
    software_version: str | None
    firmware_version: str | None
    wifi_enabled: bool
    wifi_ssid: str | None
    evse_is_three_phase: bool
    active: bool
    last_supply_grid_instant_current_l1: int | None
    last_supply_grid_instant_current_l2: int | None
    last_supply_grid_instant_current_l3: int | None
    sockets: list[DazeSocket] = field(default_factory=list)
    # Live recharge modality fetched from GET /v3/evses/{serial}.
    # The API places this value inside the nested network object:
    # network.rechargeModality (1 = standard, 2 = self-consumption/auto).
    recharge_modality: int | None = None

    @classmethod
    def from_dict(cls, raw: dict) -> DazeEvse:
        return cls(
            serial_number=raw["serialNumber"], evse_name=raw.get("evseName"),
            device_profile=raw.get("deviceProfile"), software_version=raw.get("softwareVersion"),
            firmware_version=raw.get("firmwareVersion"), wifi_enabled=bool(raw.get("wifiEnabled", False)),
            wifi_ssid=raw.get("wifiSSID"), evse_is_three_phase=bool(raw.get("evseIsThreePhase", False)),
            active=bool(raw.get("active", False)),
            last_supply_grid_instant_current_l1=raw.get("lastSupplyGridInstantCurrentL1"),
            last_supply_grid_instant_current_l2=raw.get("lastSupplyGridInstantCurrentL2"),
            last_supply_grid_instant_current_l3=raw.get("lastSupplyGridInstantCurrentL3"),
            sockets=[DazeSocket.from_dict(s) for s in raw.get("sockets", [])],
            recharge_modality=_first_int(
                raw, "rechargeModality", "currentRechargeModality"
            )
            or _first_int(
                raw.get("network") or {},
                "rechargeModality", "currentRechargeModality"
            ),
        )

    def apply_evse_details(self, raw: dict) -> None:
        """Merge live configuration from GET /v3/evses/{serial}."""
        network = raw.get("network") or {}
        modality = _first_int(
            raw, "rechargeModality", "currentRechargeModality"
        )
        if modality is None:
            modality = _first_int(
                network, "rechargeModality", "currentRechargeModality"
            )
        if modality is not None:
            self.recharge_modality = modality

        # The web service exposes the configured maximum current in the EVSE
        # response. Keep it on the primary socket so the HA number entity can
        # use the same live value as the existing current sensor.
        max_current = _first_int(
            raw,
            "maxExternalChargingCurrentInMilliAmps",
            "maxChargingCurrentInMilliAmps",
            "maxExternalChargingCurrent",
            "maxChargingCurrent",
            "lastMaxChargingCurrent",
        )
        if max_current is not None:
            socket = next(
                (s for s in self.sockets if s.is_primary),
                self.sockets[0] if self.sockets else None,
            )
            if socket is not None:
                socket.last_max_charging_current = max_current


@dataclass
class DazeNetworkData:
    network: DazeNetwork
    evses: list[DazeEvse] = field(default_factory=list)


@dataclass
class DazeAccountData:
    identity_id: str
    networks: dict[str, DazeNetworkData] = field(default_factory=dict)
