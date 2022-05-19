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
from typing_extensions import Self

import httpx

from ..errors import InvalidCookie, RetryError, UnhandledResponse

log = logging.getLogger(__name__)


class User:
    def __init__(self, security_cookie: str, proxies: dict = None):
        """
        security_cookie - roblosecurity cookie to use
        proxies - optional proxy dict to use for ALL requests done with this user
        """
        self.__roblosecurity = f"_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_{security_cookie.split('_')[-1].strip()}"
        self.__proxies = proxies

        self._client = httpx.AsyncClient(proxies=proxies)
        self._client.cookies.set(".ROBLOSECURITY", self.__roblosecurity)

        self.__last_updated_inventory = None

    async def __aenter__(self) -> None:
        """
        Context manager version of User.create
        """
        await self._authenticate()

    async def __aexit__(self, *args, **kwargs) -> None:
        await self.close()

    @classmethod
    async def create(cls, *args, **kwargs) -> Self:
        """
        Factory method creation of User object returns User
        Initializes the user class, checking the cookie's validity in the process
            security_cookie - roblosecurity cookie to login with
            proxies - optional proxies dict to use for ALL requests done
        """
        self = User(*args, **kwargs)
        await self._authenticate()
        return self

    async def close(self) -> None:
        await self._client.aclose()

    async def __request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """
        General purpose low level request handling systems
        """

        # init csrf token if needed
        try:
            if self._client.cookies.get("X-CSRF-TOKEN") is None:
                c = await self._client.request(
                    "post", "https://auth.roblox.com/v1/logout"
                )
                self._client.cookies.set("X-CSRF-TOKEN", c.headers["x-csrf-token"])
        except KeyError:
            if c.status_code == 401:
                raise InvalidCookie(
                    self.__roblosecurity,
                    response_code=c.status_code,
                    url=c.url,
                )
            raise UnhandledResponse(c, url=c.url, proxy=self.__proxies)

        ### main req & related

        method = method.upper()
        csrf = self._client.cookies.get("X-CSRF-TOKEN")
        try:
            # csrf is passed as both a cookie and a header due to roblox inconsistency
            response = await self._client.request(
                method,
                url,
                headers={"X-CSRF-TOKEN": csrf},
                **kwargs,
            )
            timed_out = False
        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError):
            timed_out = True

        # update csrf token if offered
        if (
            "x-csrf-token" in response.headers.keys()
            and response.headers["x-csrf-token"] != csrf
        ):
            self._client.cookies.set("X-CSRF-TOKEN", response.headers["x-csrf-token"])

        ### response handling

        # retries 5**, 429, and timed out responses with exponential increasing delay
        if timed_out or response.status_code >= 500 or response.status_code == 429:
            if "retries" not in locals().keys():
                retries = 1
            else:
                retries += 1

            delay = 2 ** retries

            if retries > 8:
                raise RetryError(
                    url=url,
                    retries=retries,
                    response_code=response.status_code,
                    proxy=self.__proxies,
                )
            await asyncio.sleep(delay)
            return await self.__request(method, url, retries=retries, **kwargs)

        if response.status_code == 401:
            raise InvalidCookie(
                self.__roblosecurity,
                response_code=response.status_code,
                url=response.url,
            )

        return response

    async def _authenticate(self) -> None:
        """
        Gathers basic account details and self assigns it
        """
        response = await self.__request(
            "get", "https://users.roblox.com/v1/users/authenticated"
        )

        if response.status_code == 200:
            respjson = response.json()
            self.id = int(respjson["id"])
            self.name = respjson["name"]
            self.displayname = respjson["displayName"]
            return

        raise UnhandledResponse(
            response=response, url=response.url, proxy=self.__proxies
        )

    async def get_inventory(self, user_id: int) -> list:
        """
        Returns the full inventory of the provided user
            user_id - target user roblox id
        """
        if user_id == self.id:
            return await self.inventory()

        return await self._fetch_inventory(user_id)

    async def inventory(self) -> list:
        """
        Returns the full inventory of the logged in user
        """

        # hardcoded minimum 30 second interval between rechecking own inventory
        if (
            self.__last_updated_inventory is not None
            and time.time() > self.__last_updated_inventory + 30
        ):
            return self._inv

        self._inv = await self._fetch_inventory(self.id)
        self.__last_updated_inventory = time.time()
        return self._inv

    async def _fetch_inventory(self, user_id: int, cursor: str = None) -> list:
        """
        Recursively fetches the full inventory from Roblox and returns it as a list
            user_id - target user roblox id
            cursor - optional page cursor to begin from
        """
        url = f"https://inventory.roblox.com/v1/users/{user_id}/assets/collectibles?sortOrder=Asc&limit=100"

        if cursor:
            url += f"&cursor={cursor}"

        resp = await self.__request("get", url)

        if resp.status_code != 200:
            raise UnhandledResponse(resp.status_code, url, self.__proxies)

        respjson = resp.json()
        inventory = respjson["data"]
        if respjson["nextPageCursor"]:
            # as of writing, highest # of owned items is by user 50290467 at 4500~
            # this is 45 pages, so no considerable risk for memory leak here
            # recursion depth = total_owned_count / 100 = 45
            inventory += await self._fetch_inventory(
                user_id, cursor=respjson["nextPageCursor"]
            )
        return inventory
