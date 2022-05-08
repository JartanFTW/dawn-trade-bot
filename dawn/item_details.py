import asyncio
import logging

import httpx

from database import DatabaseManager
from roblox.user import User

log = logging.getLogger(__name__)


class ItemDetailsManager:
    def __init__(
        self,
        db: DatabaseManager,
        new_collectibles_scan_delay: int = 3600,
    ):
        self.db = db
        self.new_collectibles_scan_delay = new_collectibles_scan_delay

        self._client = httpx.AsyncClient()

    async def start(self, **kwargs):
        for arg in kwargs:
            setattr(self, arg[0], arg[1])

        self.__new_collectible_scan_task = asyncio.create_task()

    async def stop(self):
        await self.__new_collectible_scan_task.cancel()

    async def close(self):
        await self.stop()
        await self._client.aclose()

    async def _new_collectables_manager(self):
        collectables, db_collectables = await asyncio.gather(
            self._get_all_item_ids(), self.db.fetchall("SELECT id FROM collectable")
        )

        for collectable in collectables:
            if int(collectable) not in db_collectables:
                pass
                # add to database
                # FUTURE TODO: queue priority data grab

        await asyncio.sleep(self.new_collectibles_scan_delay)

    async def _get_all_item_ids(self) -> list:
        """
        Scrapes and returns all item ids in a list
        """

        items = await self._get_all_collectables()
        item_ids = [x["assetId"] for x in items]
        return item_ids

    async def _get_all_collectables(
        self, cursor: str = None
    ) -> list:  # basically a copy of user.py's _get_inventory
        url = f"https://inventory.roblox.com/v1/users/1/assets/collectibles?sortOrder=Asc&limit=100"

        if cursor:
            url += f"&cursor={cursor}"

        # viewing ROBLOX user account inventory doesn't need logging in
        resp = await self._client.request("get", url)
        respjson = resp.json()
        inventory = respjson["data"]

        if respjson["nextPageCursor"]:  # recursion
            inventory += await self._get_inventory(cursor=respjson["nextPageCursor"])

        return inventory
