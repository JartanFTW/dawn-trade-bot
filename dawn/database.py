import asyncio
import logging
import os
import sys
import traceback
from typing import TypeVar

import aiosqlite
from numpy import str0

from .utils import write_file, read_file

log = logging.getLogger(__name__)

# used for typehinting creation classmethod
DBMTYPE = TypeVar("DBMTYPE", bound="DatabaseManager")


class DatabaseManager:
    def __init__(self, path: str, db_name: str, version: str):
        """
        path - the location of the database file
        db_name - the name of the database file
        version - the version of the Database running (to do version upgrade changes to database)
        """
        self.path = path
        self.name = db_name
        self.db_path = os.path.join(path, f"{db_name}.db")
        self.version = version

        # asynchronously calls self.create() and waits for its completion before continuing

    async def __aenter__(self, *args, **kwargs) -> None:
        """
        Context manager version of DatabaseManager.create
        """

        await self._setup()

        return self

    async def __aexit__(self, *args, **kwargs) -> None:
        await self.close()

    @classmethod
    async def create(self, *args, **kwargs) -> DBMTYPE:
        """
        Factory method creation of DatabaseManager object
        """
        db = DatabaseManager(*args, **kwargs)
        await db._setup()
        return db

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
            # Running schema setup
            await self._execute_script_from_file(
                os.path.join(self.path, "dawn", "schema.sql")
            )
        else:
            # update tasks
            await self._migrate()

        return self

    async def close(self) -> None:
        await self._conn.close()

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
        return self._conn

    async def _migrate(self) -> str:
        """
        Updates the database to the latest version
        Returns the new version of the database
        Returns None if no changes were made

        """
        prev_vers = await self.conn.execute(
            "PRAGMA user_version;"
        )  # query version of db
        version = await prev_vers.fetchone()
        version = version[0]

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
