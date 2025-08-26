from __future__ import annotations
from typing import Any, Dict
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import voluptuous as vol

from .const import DOMAIN, CONF_BASE_URL, CONF_API_KEY, CONF_CONTAINERS


class DockerMonitorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            base = user_input[CONF_BASE_URL]
            if base.startswith("http://") or base.startswith("https://"):
                self._data = user_input
                return await self.async_step_select_containers()
            errors["base"] = "invalid_url"

        schema = vol.Schema({
            vol.Required(CONF_BASE_URL): str,
            vol.Optional(CONF_API_KEY, default=""): str,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def _fetch_containers(self, hass: HomeAssistant, base: str, api_key: str):
        from yarl import URL
        session = async_get_clientsession(hass)
        url = str(URL(f"{base.rstrip('/')}/status").with_query({"key": api_key} if api_key else {}))
        async with session.get(url, timeout=30) as resp:
            resp.raise_for_status()
            data = await resp.json(content_type=None)
        return sorted((data.get("meta") or {}).keys())

    async def async_step_select_containers(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        base = self._data.get(CONF_BASE_URL, "")
        api_key = self._data.get(CONF_API_KEY, "")

        try:
            containers = await self._fetch_containers(self.hass, base, api_key)
        except Exception:
            errors["base"] = "cannot_fetch_containers"
            containers = []

        if user_input is not None and not errors:
            selected = [c for c in containers if user_input.get(c)]
            return self.async_create_entry(
                title="Docker Monitor",
                data=self._data,
                options={CONF_CONTAINERS: selected},
            )

        schema_dict = {}
        for c in containers:
            schema_dict[vol.Optional(c, default=True)] = bool

        return self.async_show_form(
            step_id="select_containers",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return DockerMonitorOptionsFlow(config_entry)


class DockerMonitorOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self.entry = entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        return await self.async_step_select_containers(user_input)

    async def async_step_select_containers(self, user_input: dict[str, Any] | None = None):
        from yarl import URL
        errors: dict[str, str] = {}
        base = self.entry.data.get(CONF_BASE_URL, "")
        api_key = self.entry.data.get(CONF_API_KEY, "")
        session = async_get_clientsession(self.hass)

        try:
            url = str(URL(f"{base.rstrip('/')}/status").with_query({"key": api_key} if api_key else {}))
            async with session.get(url, timeout=30) as resp:
                resp.raise_for_status()
                data = await resp.json(content_type=None)
            containers = sorted((data.get("meta") or {}).keys())
        except Exception:
            containers = []
            errors["base"] = "cannot_fetch_containers"

        current = self.entry.options.get(CONF_CONTAINERS, containers)
        if user_input is not None and not errors:
            selected = [c for c in containers if user_input.get(c)]
            return self.async_create_entry(title="", data={CONF_CONTAINERS: selected})

        schema_dict = {}
        for c in containers:
            schema_dict[vol.Optional(c, default=(c in current))] = bool

        return self.async_show_form(
            step_id="select_containers",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )