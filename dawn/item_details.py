import asyncio
import logging
import time

import httpx

from database import DatabaseManager
from roblox.user import User
from errors import UnhandledResponse

log = logging.getLogger(__name__)


class ItemDetailsManager:
    def __init__(
        self,
        db: DatabaseManager,
        new_collectibles_scan_delay: int = 3600,
    ):
        self.db = db
        self.new_collectibles_scan_delay = new_collectibles_scan_delay

        self.__last_updated_rolimons = time.time() - 60  # init -60
        self._rolimons_itemdetails = None

        self._client = httpx.AsyncClient()
        self.itemdetails = property(self._get_rolimons_itemdetails)

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
                self._update_item_data(collectable)

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

    async def _get_rolimons_itemdetails(self) -> None:
        # TODO add semaphore to prevent mass spamming rolimons api when many items are in queue for refresh
        if time.time() > self.__last_updated_rolimons + 60:
            await self._update_rolimons_itemdetails()
        return self._rolimons_itemdetails

    async def __update_rolimons_itemdetails(self) -> None:
        url = f"https://www.rolimons.com/itemapi/itemdetails"

        try:
            resp = await self._client.request("get", url)
        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError):
            # TODO ADD LOGGING (everywhere lol but especially here)
            await asyncio.sleep(60)
            # recursion opens up possible memory leaks unnecessarily. some sort of looping implementation should be done to
            # gradually increase delays between checks for the unlikely events of prolongued downtime of rolimons # an example of this was created in User.__request()
            # it's more likely for prolongued downtime to be user internet outage instead
            # this concern applies elsewhere in Dawn also. Recursion should be updated out with larger solutions in any
            # situation where we don't know the maximum recursion depth inherently (trade calculations) TODO
            return await self.__update_rolimons_itemdetails()

        if resp.status_code == 200:
            self._rolimons_itemdetails = resp.json()
            self.__last_updated_rolimons = time.time()

        raise UnhandledResponse(resp, url=resp.url)

    async def _update_item_data(self, id: int | str) -> None:
        # TODO when custom value algorithm is being implemented, change rap source to roblox themselves rather than rolimons for accuracy

        await self._get_rolimons_itemdetails()

        # api items list format because api is super minimalistic to reduce bandwidth use
        # [item_name, acronym, rap, value, default_value, demand, trend, projected, hyped, rare]
        data = (
            str(id),
            self._rolimon_itemdetails["items"][str(id)][2],
            self._rolimon_itemdetails["items"][str(id)][3],
            int(time.time()),
        )

        # maybe sql injection vulnerability? idk feedback on github please
        await self.db.conn.executescript(
            """
            UPDATE INTO 
            collectable (id, rap, roli_value, updated)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (ID) DO UPDATE SET
                rap=excluded.rap,
                roli_value=excluded.roli_value,
                updated=excluded.updated
            """,
            (
                data[0],
                data[1],
                data[2],
                data[3],
            ),  # formatting here may be wrong. needs testing
        )
