from __future__ import annotations
from typing import Any
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    api = data["api"]
    meta = (coordinator.data or {}).get("meta", {})
    selected = entry.options.get("containers")
    names = [n for n in meta.keys() if (not selected or n in selected)]

    entities: list[DockerUpdateButton] = []
    for name in names:
        metrics = meta.get(name, {})
        device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_container_{name}")},
            name=f"Docker: {name}",
            manufacturer="Docker",
            model=metrics.get("image", "container"),
        )
        entities.append(DockerUpdateButton(coordinator, api, entry.entry_id, name, device_info))
    async_add_entities(entities)

class DockerUpdateButton(CoordinatorEntity, ButtonEntity):
    def __init__(self, coordinator, api, entry_id: str, container: str, device_info: DeviceInfo) -> None:
        super().__init__(coordinator)
        self.api = api
        self._container = container
        self._attr_device_info = device_info
        self._attr_unique_id = f"{entry_id}_{container}_update_button"
        self._attr_name = "Update"
        self._attr_translation_key = "update"

    async def async_press(self) -> None:
        await self.api.trigger_update(self._container)