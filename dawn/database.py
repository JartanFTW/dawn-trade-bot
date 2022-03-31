import asyncio
import logging
import os
import sys
import traceback

import aiosqlite

log = logging.getLogger(__name__)


class Database:
    def __init__():
        pass

    @classmethod
    def create_database_file(cls, path: str, name: str) -> None:
        """
        Creates an empty database file
        Raises FileExistsError if file already exists
            path - the location to create the database file
            name - what to name the database file
        """
        db_path = os.path.join(path, f"{name}.db")
        if not os.path.isfile(db_path):
            open(db_path).close()
        else:
            raise FileExistsError(file=db_path)

    def _read_file(self, file: str) -> str:
        with open(file, "r") as stream:
            content = stream.read()
        return content

    async def _execute_script_from_file(self, file: str) -> None:
        """
        Opens and executes a the provided file as a command in another thread to prevent async blocking
            file - path of the file to open
        """
        task = asyncio.create_task(asyncio.to_thread(self._read_file(file)))
        script = await asyncio.wait(task)[0]
        await self._conn.executescript(script)

    async def _create_connection(self) -> None:
        self._conn = await aiosqlite.connect(self.db_path)

    async def _migrate(self) -> str:
        """
        Updates the database to the latest version
        Returns the new version of the database
        Returns None if no changes were made

        """
        prev_vers = self._conn.execute("PRAGMA user_version;")  # query version of db
        version = prev_vers

        # EXAMPLE:
        # doing it like this we save space and just have it incrementally update through the versions rather than having to program for every combination

        # if version == 1.0:
        #     do stuff
        #     version = 1.1 or whatever this version is changing to
        # if version == 1.1:
        #     do stuff
        #     version = 1.2

        if version == prev_vers:
            return None
        return version

    @classmethod
    async def startup(self, path: str, db_name: str, version: str) -> None:
        """
        Catch-all task that:
            1. Creates a database file if necessary
            2. Creates tables if necessary
            3. Runs update tasks based on input version
            4. Returns self

            path - the location of the database file
            db_name - the name of the database file
            version - the version of Dawn running (used to perform update changes to database)
        """
        self.path = path
        self.name = db_name
        self.db_path = os.path.join(path, f"{db_name}.db")
        self.version = version

        if not os.path.isfile(self.db_path):
            try:
                task = asyncio.create_task(
                    asyncio.to_thread(self.create_database_file(self.path, self.name))
                )
                await asyncio.gather(task)
                new_db = True
            except FileExistsError:
                pass

        await self._create_connection()

        if new_db:
            await self._execute_script_from_file(
                os.path.join(self.path, "schema.sql")
            )  # Running schema setup
        else:
            await self._migrate()  # update tasks

        return self
