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
        self.err = f"Invalid roblosecurity cookie suspected from {response_code} response calling {url}"
        super().__init__(self.err)


class UnhandledResponse(Exception):
    def __init__(
        self,
        response: str,
        url: str = None,
        proxy: str = None,
    ):
        self.response = response
        self.url = url
        self.proxy = proxy
        self.err = f"Unhandled response {response.status_code} calling {url}"
        super().__init__(self.err)


class RetryError(Exception):
    def __init__(
        self,
        url: str,
        retries: int,
        response_code: int | None,
        proxy: str | None,
    ):
        self.url = url
        self.retries = retries
        self.response_code = response_code
        self.proxy = proxy
        self.err = f"Failed to get valid response from {url} after {retries} retries"
        super().__init__(self.err)
