from __future__ import annotations
from typing import Any
from datetime import datetime, timezone

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import UnitOfInformation, UnitOfDataRate

from .const import DOMAIN, UPDATE_STATUS_KEY

_MiB = 1024 * 1024
_BITS_PER_MEGABIT = 1_000_000.0

def _to_mib(value: Any) -> float | None:
    try:
        return round(float(value) / _MiB, 1)
    except (TypeError, ValueError):
        return None

def _to_percent_1(value: Any) -> float | None:
    try:
        v = float(value)
        if 0 <= v <= 1:
            v *= 100.0
        return round(v, 1)
    except (TypeError, ValueError):
        return None

def _bytes_to_mbps(delta_bytes: float, dt_seconds: float) -> float:
    if dt_seconds <= 0:
        return 0.0
    return round((delta_bytes * 8.0) / (_BITS_PER_MEGABIT * dt_seconds), 2)

SENSOR_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="cpu", name="CPU", native_unit_of_measurement="%",
        suggested_display_precision=1, state_class=SensorStateClass.MEASUREMENT
    ),
    SensorEntityDescription(
        key="mem_perc", name="RAM %", native_unit_of_measurement="%",
        suggested_display_precision=1, state_class=SensorStateClass.MEASUREMENT
    ),
    SensorEntityDescription(
        key="mem_usage", name="RAM Usage",
        native_unit_of_measurement=UnitOfInformation.MEBIBYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        suggested_display_precision=1,
        state_class=SensorStateClass.MEASUREMENT
    ),
    SensorEntityDescription(
        key="net_rx", name="Net RX",
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        device_class=SensorDeviceClass.DATA_RATE,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT
    ),
    SensorEntityDescription(
        key="net_tx", name="Net TX",
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        device_class=SensorDeviceClass.DATA_RATE,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT
    ),
    SensorEntityDescription(
        key="blk_read", name="Block Read",
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        device_class=SensorDeviceClass.DATA_RATE,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT
    ),
    SensorEntityDescription(
        key="blk_write", name="Block Write",
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        device_class=SensorDeviceClass.DATA_RATE,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT
    ),
    SensorEntityDescription(key="state", name="State"),
    SensorEntityDescription(key=UPDATE_STATUS_KEY, name="Update Status Image"),
)

async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    payload = coordinator.data or {}
    meta = payload.get("meta", {})
    selected = entry.options.get("containers")  
    names = [n for n in meta.keys() if (not selected or n in selected)]

    entities: list[DockerSensor] = []
    for name in names:
        metrics = meta.get(name, {})
        device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_container_{name}")},
            name=f"Docker: {name}",
            manufacturer="Docker",
            model=metrics.get("image", "container"),
        )
        for desc in SENSOR_DESCRIPTIONS:
            entities.append(
                DockerSensor(
                    coordinator=coordinator,
                    entry_id=entry.entry_id,
                    container=name,
                    description=desc,
                    device_info=device_info,
                )
            )
    async_add_entities(entities)

class DockerSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry_id: str, container: str,
                 description: SensorEntityDescription, device_info: DeviceInfo) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._container = container
        self._attr_device_info = device_info
        self._attr_unique_id = f"{entry_id}_{container}_{description.key}"
        self._attr_name = description.name
        self._attr_translation_key = description.key
        self._last_sample_val: float | None = None
        self._last_sample_ts: float | None = None

    @property
    def native_value(self) -> Any:
        data = self.coordinator.data or {}
        meta = data.get("meta", {})
        updates = data.get("updates", {})
        metrics = meta.get(self._container, {})
        key = self.entity_description.key

        if key == UPDATE_STATUS_KEY:
            return updates.get(self._container)

        if key == "cpu":
            return _to_percent_1(metrics.get("cpu"))
        if key == "mem_perc":
            return _to_percent_1(metrics.get("mem_perc"))
        if key == "mem_usage":
            return _to_mib(metrics.get("mem_usage"))

        if key in {"net_rx", "net_tx", "blk_read", "blk_write"}:
            cur_raw = metrics.get(key)
            try:
                cur = float(cur_raw)
            except (TypeError, ValueError):
                return None

            if getattr(self.coordinator, "last_update_success_time", None):
                now_ts = self.coordinator.last_update_success_time.timestamp()
            else:
                now_ts = datetime.now(timezone.utc).timestamp()

            if self._last_sample_val is not None and self._last_sample_ts is not None:
                delta_bytes = max(0.0, cur - self._last_sample_val)
                dt = max(0.001, now_ts - self._last_sample_ts)
                mbps = _bytes_to_mbps(delta_bytes, dt)
            else:
                mbps = 0.0

            self._last_sample_val = cur
            self._last_sample_ts = now_ts
            return mbps

        return metrics.get(key)

    @property
    def icon(self) -> str | None:
        key = self.entity_description.key
        if key == "cpu":
            return "mdi:cpu-64-bit"
        if key in {"mem_perc", "mem_usage"}:
            return "mdi:memory"
        if key == "net_rx":
            return "mdi:download-network-outline"
        if key == "net_tx":
            return "mdi:upload-network-outline"
        if key in {"blk_read", "blk_write"}:
            return "mdi:harddisk"
        if key == "state":
            value = (self.native_value or "").lower()
            return "mdi:docker" if value == "running" else "mdi:alert-circle"
        if key == UPDATE_STATUS_KEY:
            value = (self.native_value or "").lower()
            return "mdi:check-circle" if value == "up_to_date" else "mdi:package-up"
        return super().icon