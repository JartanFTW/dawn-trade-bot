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

    def create_database_file(self, path: str, name: str) -> None:
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

    async def _create_connection(self) -> None:
        self._conn = await aiosqlite.connect(self.db_path)

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
                create_tables = True
            except FileExistsError:
                pass

        await self._create_connection()

        if create_tables:
            pass
            # create tables here

        # run update tasks here

        return self
