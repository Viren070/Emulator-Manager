from pathlib import Path
import platform

from core.logging.logger import Logger


class XeniaSettings:
    def __init__(self):
        self.logger = Logger(__name__).get_logger()
        self.default_config = {
            "install_directory": self.get_default_install_directory(),
            "portable_mode": False,
            "release_channel": "master",
            "game_directory": Path().resolve(),
        }
        self._config = self.default_config.copy()

    def reset(self):
        self.logger.info("Resetting Xenia settings")
        self._config = self.default_config.copy()

    def get_default_install_directory(self):
        system = platform.system().lower()

        if system == "windows":
            return Path.home() / "AppData" / "Local" / "Xenia"

        return Path()

    def _set_property(self, property_name, value):
        self.logger.debug(f"Setting {property_name} to {value}")
        self._config[property_name] = value

    def _get_property(self, property_name):
        return self._config.get(property_name)

    install_directory = property(
        fget=lambda self: self._get_property("install_directory"),
        fset=lambda self, value: self._set_property("install_directory", value),
    )

    portable_mode = property(
        fget=lambda self: self._get_property("portable_mode"),
        fset=lambda self, value: self._set_property("portable_mode", value),
    )

    release_channel = property(
        fget=lambda self: self._get_property("release_channel"),
        fset=lambda self, value: self._set_property("release_channel", value),
    )
    game_directory = property(
        fget=lambda self: self._get_property("game_directory"),
        fset=lambda self, value: self._set_property("game_directory", value),
    )
