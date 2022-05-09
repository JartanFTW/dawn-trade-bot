import asyncio
from contextlib import asynccontextmanager
import logging
import time

import httpx

log = logging.getLogger(__name__)


class InvalidCookie(Exception):
    def __init__(
        self,
        cookie: str,
        response_code: int = None,
        url: str = None,
        proxy: str = None,
    ):
        self.cookie = cookie
        self.response_code = response_code
        self.url = url
        self.proxy = proxy
        self.err = f"Invalid roblosecurity cookie suspected from response {response_code} calling {url}"
        super().__init__(self.err)


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

        self._client = httpx.AsyncClient(proxies=proxies)
        self._client.cookies.set(".ROBLOSECURITY", self._roblosecurity)

        await self._authenticate()

        return self

    async def close(self):
        await self._client.aclose()

    async def __request(self, method: str, url: str, **kwargs) -> httpx.Response:

        method = method.upper()

        # updates csrf token if needed
        if method != "get" and self._client.cookies.get("X-CSRF-TOKEN") == None:
            c = await self._client.request("post", "https://auth.roblox.com/v1/logout")
            self._client.cookies.set("X-CSRF-TOKEN", c.headers["x-csrf-token"])

        # main req
        csrf = self._client.cookies.get("X-CSRF-TOKEN")
        response = await self._client.request(
            method,
            url,
            headers={"X-CSRF-TOKEN": csrf},
            **kwargs,
        )
        # TODO add handling for httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError and all 500 responses

        # keeps latest csrf token updated
        if (
            "x-csrf-token" in response.headers.keys()
            and response.headers["x-csrf-token"] != csrf
        ):
            self._client.cookies.set("X-CSRF-TOKEN", response.headers["x-csrf-token"])

        if response.status_code == 401:
            raise InvalidCookie(
                self._roblosecurity,
                response_code=response.status_code,
                url=response.url,
            )

        # TODO add 429 handling

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

        # TODO add raise unknownresponse

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
