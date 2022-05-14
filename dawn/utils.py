import asyncio
from configparser import ConfigParser, SectionProxy
import logging
import os
import time

log = logging.getLogger(__name__)


def format_print(text: str, log_level: int = None) -> None:
    """
    Prints to console the provided string with a H:M:S | timestamp
        text - the text to print
        log_level - optional level to log the text as
    """

    formatted_text = time.strftime("%H:%M:%S | ", time.localtime()) + text
    print(formatted_text)
    if isinstance(log_level, int):
        log.log(log_level, text)


def load_config(path: str) -> dict:
    """
    Loads the provided file via ConfigParser and returns it with some formatting magic
        path - the path to the config file
    """

    parser = ConfigParser()
    parser.read(path)

    def wrap_to_dict(to_wrap):
        wrapped = dict(to_wrap)
        for key, value in wrapped.items():
            if isinstance(value, ConfigParser) or isinstance(value, SectionProxy):
                wrapped[key] = wrap_to_dict(value)
            elif value.upper().strip() in ("TRUE", "FALSE"):
                wrapped[key] = True if value.upper().strip() == "TRUE" else False
            else:
                try:
                    wrapped[key] = int(value)
                except ValueError:
                    pass
        return wrapped

    config = wrap_to_dict(parser)
    return config


def setup_logging(path: str, level: int = 40) -> None:
    """
    Uses basicConfig to setup logging at the provided home path and level.
        path - the location to create the logs folder
        level - the log level to begin logging messages at
    https://docs.python.org/3/howto/logging.html#logging-levels
    """

    logs_folder_path = os.path.join(path, "logs")

    if not os.path.exists(logs_folder_path):
        os.makedirs(logs_folder_path)
    log_path = os.path.join(
        logs_folder_path, time.strftime("%Y-%m-%d", time.localtime())
    )
    logging.basicConfig(
        filename=f"{log_path}.log",
        level=level,
        format="%(asctime)s:%(levelname)s:%(message)s",
    )


def write_file(file: str, content: str = None) -> None:
    if not content:
        content = ""
    with open(file, "w") as stream:
        stream.write(content)


def read_file(file: str) -> str:
    with open(file, "r") as stream:
        content = stream.read()
    return content
