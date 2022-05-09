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


class UnhandledResponse(Exception):
    def __init__(self, response: str):
        self.response = response
        self.err = f"Unhandled response {response.status_code}"
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
