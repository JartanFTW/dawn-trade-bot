# Dawn Trade Bot
# Copyright (C) 2022  Jonathan Carter

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
import asyncio
import logging
import time

import httpx

from .database import DatabaseManager
from .roblox.user import User
from .errors import UnhandledResponse

log = logging.getLogger(__name__)


class ItemDetailsManager:
    def __init__(
        self,
        db: DatabaseManager,
        new_collectibles_scan_delay: int = 3600,
        update_collectables_delay: int = 60,
    ):
        log.info("Initializing Item Details Manager")

        self.db = db
        self.new_collectibles_scan_delay = new_collectibles_scan_delay
        self.update_collectables_delay = update_collectables_delay

        self.__last_updated_rolimons = time.time() - 60  # init -60
        self._rolidetails = None

        self.itemdetails = property(self._get_rolidetails)
        self.__rolimons_semaphore = asyncio.Semaphore(1)

    async def start(self, **kwargs):
        """
        Starts worker tasks - stop with ItemDetailsManager.stop()
        """

        log.info("Starting Item Details Manager")

        # starting httpx client in here to remove need for close, making only stop necessary
        self._client = httpx.AsyncClient()

        for arg in kwargs:  # TODO change to named optional parameters for delays
            setattr(self, arg[0], arg[1])

        self.__new_collectables_worker_task = asyncio.create_task(
            self._new_collectables_worker()
        )
        self.__existing_collectables_worker_task = asyncio.create_task(
            self._existing_collectables_worker()
        )

    async def stop(self):
        """
        Stops worker tasks - start with ItemDetailsManager.start()
        """

        log.info("Stopping Item Details Manager")

        self.__new_collectables_worker_task.cancel()
        self.__existing_collectables_worker_task.cancel()

        await self._client.aclose()

    async def _new_collectables_worker(self):
        """
        Periodically grabs the inventory of user 1 and compares to collectables entered in database
        If new collectables are detected, enters into database
        """

        log.debug("New collectables worker beginning")

        while True:
            collectables, db_collectables = await asyncio.gather(
                self._get_all_item_ids(), self.db.fetchall("SELECT id FROM collectable")
            )

            for collectable in collectables:
                if int(collectable) not in db_collectables:
                    await self._update_item_data(collectable)
            await asyncio.sleep(self.new_collectibles_scan_delay)

    async def _existing_collectables_worker(self):
        """
        Periodically queries the database collectables table, updating entries that haven't been updated recently
        """

        log.debug("Existing collectables worker beginning")

        while True:
            collectables = await self.db.fetchall("SELECT id FROM collectable")

            # choosing to do iterative approach rather than spawning lots of asynchronous tasks to prevent large memory spikes
            # if speed is a noticeable issue, can implement some sort of batching
            for id in collectables:
                await self._update_item_data(id)

            await asyncio.sleep(self.update_collectables_delay)

    async def _get_all_item_ids(self) -> list:
        """
        Scrapes and returns all ROBLOX item ids into a list
        """

        log.debug("Scraping all collectable item ids")

        items = await self.__get_all_collectables()
        item_ids = [x["assetId"] for x in items]
        return item_ids

    async def __get_all_collectables(
        self, cursor: str = None
    ) -> list:  # basically a copy of user.py's _fetch_inventory
        """
        Grabs all collectables from the inventory of the user ROBLOX (id 1), which is one copy of every item
            cursor - page to start from
        """
        url = f"https://inventory.roblox.com/v1/users/1/assets/collectibles?sortOrder=Asc&limit=100"

        if cursor:
            url += f"&cursor={cursor}"

        # viewing ROBLOX user account inventory doesn't need logging in
        resp = await self._client.request("get", url)
        respjson = resp.json()
        inventory = respjson["data"]

        if respjson["nextPageCursor"]:  # recursion
            inventory += await self.__get_all_collectables(
                cursor=respjson["nextPageCursor"]
            )

        return inventory

    async def _get_rolidetails(self) -> dict:
        """
        Returns rolimons itemdetails data updated within the last minute
        """

        log.info("Getting rolidetails")

        # semaphore encompasses time check else it'd spam rolimons one by one pointlessly
        async with self.__rolimons_semaphore:
            if time.time() > self.__last_updated_rolimons + 60:
                await self.__update_rolimons_itemdetails()
        return self._rolidetails

    async def __update_rolimons_itemdetails(self) -> None:
        """
        Updates class _rolidetails
        _rolidetails format:
        [item_name, acronym, rap, value, default_value, demand, trend, projected, hyped, rare]
        """

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
            self._rolidetails = resp.json()
            self.__last_updated_rolimons = time.time()
            return

        raise UnhandledResponse(resp, url=resp.url)

    async def _update_item_data(self, id: int) -> None:
        """
        Updates database collectable table for the provided item id
            id - the collectable id to update
        """

        # TODO when custom value algorithm is being implemented, change rap source to roblox themselves rather than rolimons for accuracy

        rolidetails = await self._get_rolidetails()

        data = (
            str(id),
            rolidetails["items"][str(id)][2],
            rolidetails["items"][str(id)][3],
            int(time.time()),
        )

        await self.db.conn.execute(
            """
            INSERT INTO 
            collectable (id, rap, roli_value, updated)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (ID) DO UPDATE SET
                rap=excluded.rap,
                roli_value=excluded.roli_value,
                updated=excluded.updated
            """,
            parameters=data,
        )
        await self.db.conn.commit()
