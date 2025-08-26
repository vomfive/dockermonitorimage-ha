from __future__ import annotations
from typing import Any, Dict, Optional
from aiohttp import ClientSession
from yarl import URL

class DockerMonitorAPI:
    def __init__(
        self,
        session: ClientSession,
        base_url: str,
        api_key: Optional[str],
        update_path: str,
        force_on_poll: bool,
    ) -> None:
        self._session = session
        self._base = base_url.rstrip("/")
        self._key = api_key or ""
        self._update = update_path if update_path.startswith("/") else "/" + update_path
        self._force = force_on_poll

    def _with_params(self, url: str, force: Optional[bool] = None) -> str:
        u = URL(url)
        q = dict(u.query)
        if self._key:
            q["key"] = self._key
        if force is True or (force is None and self._force):
            q["force"] = "1"
        return str(u.with_query(q))

    async def get_status(self) -> Dict[str, Any]:
        url = self._with_params(f"{self._base}/status")
        async with self._session.get(url, timeout=60) as resp:
            resp.raise_for_status()
            return await resp.json(content_type=None)

    async def get_status_container(self, name: str) -> Dict[str, Any]:
        url = self._with_params(f"{self._base}/status/{name}")
        async with self._session.get(url, timeout=60) as resp:
            resp.raise_for_status()
            return await resp.json(content_type=None)

    async def trigger_update(self, container: str) -> Dict[str, Any]:
        url = f"{self._base}{self._update}"
        if self._key:
            url = str(URL(url).with_query({"key": self._key}))
        payload = {"name": container}
        async with self._session.post(url, json=payload, timeout=60) as resp:
            resp.raise_for_status()
            try:
                return await resp.json(content_type=None)
            except Exception:
                return {"status": "unknown"}