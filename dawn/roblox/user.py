import asyncio
from datetime import datetime
import logging

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
        pass

    def __del__(self):
        if isinstance(self._client, property):
            asyncio.create_task(self._client.aclose())

    @classmethod
    async def create(cls, security_cookie: str, proxies: dict = None):
        """
        Initializes the user class, checking the cookie's validity in the process
        Returns User
            security_cookie - roblosecurity cookie to use
            proxy - optional proxy dict to use for initialization requests
        """
        self = User()

        self._roblosecurity = f"_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_{security_cookie.split('_')[-1].strip()}"

        self._client = httpx.AsyncClient(cookies={})
        self._client.cookies[".ROBLOSECURITY"] = self._roblosecurity

        await self._authenticate(proxies=proxies)  # grab user data thus checks cookie

        return self

    async def _request(self, method: str, url: str, **kwargs):
        method = method.lower()

        response = await self._client.Request(method, url, **kwargs)
        if method != "get":
            if "x-csrf-token" in response.headers.keys():
                self._client.cookies["X-CSRF-TOKEN"] = response.headers["x-csrf-token"]
                if response.status_code == 403:
                    response = await self._client.Request(method, url, **kwargs)

        if response.status_code == 401:
            raise InvalidCookie(
                self._roblosecurity,
                response_code=response.status_code,
                url=response.url,
            )

        return response

    async def _authenticate(self, proxies: dict = None) -> bool | None:
        response = await self.client._request(
            "get", "https://users.roblox.com/v1/users/authenticated", proxies=proxies
        )

        if response.status_code == 200:
            respjson = response.json()
            self.id = respjson["id"]
            self.name = respjson["name"]
            self.displayname = respjson["displayName"]
            return True

        return False

    async def get_inventory(self, user_id: str | int, proxies: dict = None) -> list:
        """
        Returns the full inventory of the provided user
        """
        if user_id == self.id:
            return await self.inventory(proxies=proxies)

        return await self._get_inventory(user_id, proxies=proxies)

    async def inventory(self, proxies: dict = None) -> list:
        """
        Returns the full inventory of the associated user
        """

        if (
            self._last_updated_inventory
            and (datetime.now() - self._last_updated_inventory).seconds < 30
        ):  # hardcoding minimum 30 second interval between rechecking inventory
            return self._inv

        self._inv = await self._get_inventory(self.id, proxies=proxies)
        self._last_updated_inventory = datetime.now()
        return self._inv

    async def _get_inventory(
        self, user_id: str | int, cursor: str = None, proxies: dict = None
    ):
        url = f"https://inventory.roblox.com/v1/users/{user_id}/assets/collectibles?sortOrder=Asc&limit=100"

        if cursor:
            url += f"&cursor={cursor}"

        resp = self._request("get", url, proxies=proxies)
        respjson = resp.json()
        inventory = respjson["data"]
        if respjson["nextPageCursor"]:
            inventory += await self._get_inventory(
                user_id, cursor=respjson["nextPageCursor"], proxies=proxies
            )
        return inventory
