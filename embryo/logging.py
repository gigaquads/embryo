from ravel.logging import ConsoleLoggerInterface

from .constants import EMBRYO_CONSOLE_LOG_LEVEL


logger = ConsoleLoggerInterface(
    'embryo', level=EMBRYO_CONSOLE_LOG_LEVEL
)
