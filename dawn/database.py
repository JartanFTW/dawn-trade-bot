import asyncio
from contextlib import asynccontextmanager
import logging
import os
import sys
import traceback

import aiosqlite

log = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self):
        self.conn = property(self._get_conn)  # getter function
        pass

    @asynccontextmanager
    async def __context_create(self, path: str, db_name: str, version: str):
        """
        Context manager version of DatabaseManager.create
        """

        await self.create(path, db_name, version)

        try:
            yield self
        finally:
            await self.close()

    async def create(self, path: str, db_name: str, version: str) -> None:
        """
        Catch-all factory method that:
            1. Creates a database file if necessary
            2. Creates tables if necessary
            3. Runs update tasks based on input version
            4. Returns self

            path - the location of the database file
            db_name - the name of the database file
            version - the version of the Database running (to do version upgrade changes to database)
        """
        self.path = path
        self.name = db_name
        self.db_path = os.path.join(path, f"{db_name}.db")
        self.version = version

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
            await self._execute_script_from_file(os.path.join(self.path, "schema.sql"))
        else:
            # update tasks
            await self._migrate()

        return self

    async def close(self) -> None:
        await self._conn.close()

    @classmethod
    async def create_database_file(cls, path: str, name: str) -> None:
        """
        Creates an empty database file
        Raises FileExistsError if file already exists
            path - the location to create the database file
            name - what to name the database file
        """
        db_path = os.path.join(path, f"{name}.db")
        if not os.path.isfile(db_path):
            task = asyncio.create_task(asyncio.to_thread(open(db_path).close()))
            await asyncio.wait(task)
        else:
            raise FileExistsError(file=db_path)

    def __read_file(self, file: str) -> str:
        # comment below is possible improvement to remove repeated code, but need to test before implementing TODO
        # asyncio.to_thread(content = open(file, "r").read())
        with open(file, "r") as stream:
            content = stream.read()
        return content

    async def _execute_script_from_file(self, file: str) -> None:
        """
        Opens and executes a the provided file as a command in another thread to prevent async blocking
            file - path of the file to open
        """
        task = asyncio.create_task(asyncio.to_thread(self.__read_file(file)))
        script = await asyncio.gather(task)[0]
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

    def _get_conn(self) -> aiosqlite.Connection:
        # TODO add check that connection is active, and handle if not
        return self._conn

    async def _migrate(self) -> str:
        """
        Updates the database to the latest version
        Returns the new version of the database
        Returns None if no changes were made

        """
        prev_vers = self.conn.execute("PRAGMA user_version;")  # query version of db
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
