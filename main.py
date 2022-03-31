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
import os
import sys
import traceback

from dawn import utils, load_proxies


VERSION = "PRE"
TITLE = "DAWN TRADE BOT"


if getattr(sys, "frozen", False):  # Check if program is compiled to exe
    PATH = os.path.dirname(sys.executable)
else:
    PATH = os.path.dirname(os.path.abspath(__file__))


log = logging.getLogger("main")


async def main():

    config = utils.load_config(os.path.join(PATH, "config.ini"))
    try:
        utils.setup_logging(PATH, config["DEBUG"]["logging_level"])
    except KeyError:
        utils.setup_logging(PATH)

    try:
        proxies = await load_proxies(os.path.join(PATH, "proxies.txt"))
    except FileNotFoundError:
        proxies = None

    return


if __name__ == "__main__":
    asyncio.run(main())
