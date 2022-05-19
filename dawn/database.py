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
from typing_extensions import Self

import aiosqlite

from .utils import write_file, read_file

log = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, path: str, db_name: str):
        """
        path - path to containing folder of the db file
        db_name - the name of the database file
        """
        self.path = path
        self.name = db_name
        self.db_path = os.path.join(path, f"{db_name}.db")

    async def __aenter__(self) -> None:
        """
        Context manager version of DatabaseManager.create
        """
        await self._setup()
        return self

    async def __aexit__(self, *args, **kwargs) -> None:
        await self.close()

    @classmethod
    async def create(cls, *args, **kwargs) -> Self:
        """
        Factory method creation of DatabaseManager object returns DatabaseManager
        Calls setup processes and handles migration
            path - path to containing folder of the db file
            db_name - the name of the database file
        """
        self = DatabaseManager(*args, **kwargs)
        await self._setup()
        return self

    async def close(self) -> None:
        await self._conn.close()

    async def _setup(self):
        """
        Catch-all process that:
            1. Creates a database file if necessary
            2. Creates tables if necessary
            3. Runs update tasks based on input version
            4. Returns self
        """
        new_db = False

        # creating database file if it doesn't exist
        if not os.path.isfile(self.db_path):
            try:
                await self.create_database_file(self.path, self.name)
                new_db = True
            except FileExistsError:
                pass

        # creating connection
        await self._create_connection()

        if new_db:
            # running schema setup
            await self._execute_script_from_file(
                os.path.join(self.path, "dawn", "schema.sql")
            )
        else:
            # update tasks
            await self._migrate()

        return self

    async def create_database_file(self, path: str, name: str) -> None:
        """
        Creates an empty database file
        Raises FileExistsError if file already exists
            path - the location to create the database file
            name - what to name the database file
        """
        db_path = os.path.join(path, f"{name}.db")
        if not os.path.isfile(db_path):
            await asyncio.to_thread(write_file, db_path)
        else:
            raise FileExistsError(file=db_path)

    async def _execute_script_from_file(self, file: str) -> None:
        """
        Opens and executes a the provided file as a command in another thread to prevent async blocking
            file - path of the file to open
        """
        script = await asyncio.to_thread(read_file, file)
        await self.conn.executescript(script)

    async def _create_connection(self) -> None:
        self._conn = await aiosqlite.connect(self.db_path)

    async def fetchone(self, query: str):
        """
        Queries and fetches one matching line from the database
            query - the query to execute on the database
        """

        cursor = await self.conn.execute(query)
        row = await cursor.fetchone()
        await cursor.close()
        return row

    async def fetchall(self, query: str):
        """
        Queries and fetches all matching lines from the database
            query - the query to execute on the database
        """

        cursor = await self.conn.execute(query)
        rows = await cursor.fetchall()
        await cursor.close()
        return rows

    @property
    def conn(self) -> aiosqlite.Connection:
        # TODO add check that connection is active, and handle if not
        # not doing this unless problems arise that demand it
        return self._conn

    async def _migrate(self) -> int | None:
        """
        Updates the database to the latest version
        Returns the new version of the database
        Returns None if no changes were made

        """
        prev_vers = await self.fetchone("PRAGMA user_version;")  # query version of db
        prev_vers = prev_vers[0]
        version = prev_vers

        # EXAMPLE:
        # doing it like this we save space and just have it incrementally update through the versions rather than having to program for every combination

        # if version == 1.0:
        #     do stuff IN ANOTHER FUNCTION
        #     version = 1.1 or whatever this version is changing to
        # if version == 1.1:
        #     do stuff IN ANOTHER FUNCTION
        #     version = 1.2

        if version == prev_vers:
            return None
        return version
