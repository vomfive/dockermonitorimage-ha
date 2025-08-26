from __future__ import annotations
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CONF_BASE_URL, CONF_API_KEY, DEFAULT_UPDATE_PATH
from .api import DockerMonitorAPI
from .coordinator import DockerDataCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    api = DockerMonitorAPI(
        session=session,
        base_url=entry.data[CONF_BASE_URL],
        api_key=entry.data.get(CONF_API_KEY),
        update_path=DEFAULT_UPDATE_PATH,   
        force_on_poll=True,                
    )
    coordinator = DockerDataCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"api": api, "coordinator": coordinator}
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok