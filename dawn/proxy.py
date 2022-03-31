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
