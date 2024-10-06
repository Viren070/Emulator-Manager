import logging

from core.config.constants import App


class Logger:
    def __init__(self, name):
        # Configure the logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # clear handlers to avoid duplicate logs
        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        # Create a formatter that includes the timestamp with milliseconds
        formatter = logging.Formatter(
            '[%(asctime)s.%(msecs)03d] [%(levelname)s] [%(name)s.%(funcName)s]: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Create a console handler and set the log level
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        # create a file handler and set the log level
        try:
            file_handler = logging.FileHandler(f"{App.NAME.value}.log")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        except PermissionError:
            # in case of permission error, log to console
            self.logger.error("Permission denied to write to log file")

    def get_logger(self):
        return self.logger
