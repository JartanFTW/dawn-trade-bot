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


async def load_proxies(path: str) -> list:
    """
    Loads proxies from file
    Returns the proxies as list separated by line
        path - path to the file to load
    """

    def load(path: str) -> list:
        with open(path, "r") as file:
            return file.readlines()

    task = asyncio.create_task(asyncio.to_thread(load(path)))
    proxies = await asyncio.gather(task)[0]

    proxies = [
        proxy for proxy in proxies if proxy
    ]  # hopefully get's rid of blank lines?

    return proxies
