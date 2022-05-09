import asyncio
from contextlib import asynccontextmanager
import logging
import time

import httpx

from ..errors import InvalidCookie, RetryError, UnhandledResponse

log = logging.getLogger(__name__)


class User:
    def __init__(self):
        self._last_updated_inventory = None

    @asynccontextmanager
    async def __context_create(self, security_cookie: str, proxies: dict = None):
        """
        Context manager version of User.create
        """

        await self.create(security_cookie, proxies)

        try:
            yield self
        finally:
            await self.close()

    async def create(self, security_cookie: str, proxies: dict = None):
        """
        Initializes the user class, checking the cookie's validity in the process
        Returns User
            security_cookie - roblosecurity cookie to use
            proxy - optional proxy dict to use for ALL requests done with this user
        """

        self._roblosecurity = f"_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_{security_cookie.split('_')[-1].strip()}"
        self._proxies = proxies

        self._client = httpx.AsyncClient(proxies=proxies)
        self._client.cookies.set(".ROBLOSECURITY", self._roblosecurity)

        await self._authenticate()

        return self

    async def close(self):
        await self._client.aclose()

    async def __request(self, method: str, url: str, **kwargs) -> httpx.Response:

        method = method.upper()

        # init csrf token if needed
        if self._client.cookies.get("X-CSRF-TOKEN") is None:
            c = await self._client.request("post", "https://auth.roblox.com/v1/logout")
            self._client.cookies.set("X-CSRF-TOKEN", c.headers["x-csrf-token"])

        # main req
        csrf = self._client.cookies.get("X-CSRF-TOKEN")
        try:
            response = await self._client.request(
                method,
                url,
                headers={"X-CSRF-TOKEN": csrf},
                **kwargs,
            )
            timed_out = False
        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError):
            # TODO add logging
            timed_out = True

        # keeps latest csrf token updated
        if (
            "x-csrf-token" in response.headers.keys()
            and response.headers["x-csrf-token"] != csrf
        ):
            self._client.cookies.set("X-CSRF-TOKEN", response.headers["x-csrf-token"])

        ### response handling below

        # retries 5**, 429, and timed out responses with exponential increasing delay
        if timed_out or response.status_code >= 500 or response.status_code == 429:
            if not hasattr(self, "_retries"):
                self._retries = 1
            else:
                self._retries += 1

            delay = 2 ** self._retries

            if self._retries > 8:
                raise RetryError(
                    url=url,
                    retries=self._retries,
                    response_code=response.status_code,
                    proxy=self._proxies,
                )

            # TODO logging
            await asyncio.sleep(delay)
            return await self.__request(method, url, **kwargs)

        if response.status_code == 401:
            raise InvalidCookie(
                self._roblosecurity,
                response_code=response.status_code,
                url=response.url,
            )

        ### end response handling

        return response

    async def _authenticate(self) -> None:
        response = await self.client.__request(
            "get", "https://users.roblox.com/v1/users/authenticated"
        )

        if response.status_code == 200:
            respjson = response.json()
            self.id = respjson["id"]
            self.name = respjson["name"]
            self.displayname = respjson["displayName"]
            return

        raise UnhandledResponse(
            response=response, url=response.url, proxy=self._proxies
        )

    async def get_inventory(self, user_id: str | int) -> list:
        """
        Returns the full inventory of the provided user
            user_id - id of the user
        """
        if int(user_id) == int(self.id):
            return await self.inventory()

        return await self._get_inventory(user_id)

    async def inventory(self) -> list:
        """
        Returns the full inventory of the class associated user
        """

        # hardcoding minimum 30 second interval between rechecking own inventory
        if (
            self._last_updated_inventory
            and time.time() > self._last_updated_inventory + 30
        ):
            return self._inv

        self._inv = await self._get_inventory(self.id)
        self._last_updated_inventory = time.time()
        return self._inv

    async def _get_inventory(self, user_id: str | int, cursor: str = None) -> list:
        url = f"https://inventory.roblox.com/v1/users/{user_id}/assets/collectibles?sortOrder=Asc&limit=100"

        if cursor:
            url += f"&cursor={cursor}"

        resp = self.__request("get", url)
        # TODO add check for correct response code & handle otherwise
        respjson = resp.json()
        inventory = respjson["data"]
        if respjson["nextPageCursor"]:
            # recursion depth = total_collectables_count / 100 = currently around 22 pages increasing VERY slowly (non-problem)
            inventory += await self._get_inventory(
                user_id, cursor=respjson["nextPageCursor"]
            )
        return inventory
