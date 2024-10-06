import json
from pathlib import Path

from core.config.assets import Assets
from core.config.paths import Paths
from core.emulators.dolphin.settings import DolphinSettings
from core.emulators.ryujinx.settings import RyujinxSettings
from core.emulators.xenia.settings import XeniaSettings
from core.emulators.yuzu.settings import YuzuSettings
from core.logging.logger import Logger


class Settings:
    def __init__(self, paths: Paths):
        self.logger = Logger(__name__).get_logger()
        self.paths = paths
        self.assets = Assets(paths)
        self.default_settings = {
            "dark_mode": True,
            "colour_theme_path": self.assets.get_theme_path("blue"),
            "delete_files_after_installing": True,
            "auto_app_updates": True,
            "auto_emulator_updates": True,
            "announcements_read": [],
            "firmware_denied": False,
            "token": ""

        }

        self.settings_file = self.paths.settings_file

        self._settings = self.default_settings.copy()
        self.dolphin = DolphinSettings()
        self.ryujinx = RyujinxSettings()
        self.yuzu = YuzuSettings()
        self.xenia = XeniaSettings()
        self.version = "5"
        if self.settings_file_valid():
            self.load()
        else:
            self.create_settings_file()
            self.load()

    def reset(self):
        self.logger.info("Resetting settings")
        self._settings = self.default_settings.copy()
        self.dolphin.reset()
        self.ryujinx.reset()
        self.yuzu.reset()
        self.xenia.reset()
        self.save()

    def settings_file_valid(self):
        if not self.settings_file.exists():
            self.logger.info("Settings file does not exist")
            return False
        try:
            with open(self.settings_file, "r", encoding="utf-8") as file:
                settings = json.load(file)
                if settings["version"] != self.version:  # and not self.upgrade_if_possible(settings["version"]):
                    return False
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return False

        return True

    def create_settings_file(self):
        settings_template = {
            "version": self.version,

            "dolphin_settings": {
                "install_directory": "",
                "portable_mode": "",
                "game_directory": "",
                "release_channel": ""

            },
            "yuzu_settings": {
                "portable_mode": "",
                "install_directory": "",
                "release_channel": ""

            },
            "ryujinx_settings": {
                "portable_mode": "",
                "install_directory": ""
            },
            "xenia_settings": {
                "portable_mode": "",
                "install_directory": "",
                "game_directory": "",
                "release_channel": "",
            },
            "app_settings": {
                "dark_mode": "",
                "colour_theme_path": "",
                "delete_files_after_installing": "",
                "auto_app_updates": "",
                "auto_emulator_updates": "",
                "firmware_denied": ""
            }
        }

        self.settings_file.resolve().parent.mkdir(parents=True, exist_ok=True)

        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump(settings_template, f, indent=4)

    def load(self):
        self.logger.info("Loading settings")
        with open(self.settings_file, "r", encoding="utf-8") as file:
            settings = json.load(file)

        sections = {
            "dolphin_settings": self.dolphin,
            "yuzu_settings": self.yuzu,
            "ryujinx_settings": self.ryujinx,
            "xenia_settings": self.xenia,
            "app_settings": self
        }

        for section_name, section_obj in sections.items():
            if section_name not in settings:
                continue
            section_settings = settings[section_name]
            for setting_name, value in section_settings.items():
                if value == "":
                    continue
                if "path" in setting_name or "directory" in setting_name and value:
                    value = Path(value) if value else value
                    if "directory" in setting_name:
                        value.mkdir(parents=True, exist_ok=True)
                try:
                    # Set the value from the settings file
                    setattr(section_obj, setting_name, value)
                except Exception as error:
                    self.logger.error(f"Error loading setting {setting_name} from section {section_name}: {error}")
                    # If the value is invalid, simply ignore it as
                    # we are in the initialisation stage and cannot
                    # display error messages

    def save(self):
        # when saving the settings, we need to convert Path objects to strings
        settings = {

            "version": self.version,

            "dolphin_settings": {
                "install_directory": str(self.dolphin.install_directory.resolve()),
                "portable_mode": self.dolphin.portable_mode,
                "sync_user_data": self.dolphin.sync_user_data,
                "game_directory": str(self.dolphin.game_directory.resolve()),
                "release_channel": self.dolphin.release_channel,
                "last_used_data_path": str(self.dolphin.last_used_data_path)
            },
            "yuzu_settings": {
                "install_directory": str(self.yuzu.install_directory.resolve()),
                "release_channel": self.yuzu.release_channel,
                "portable_mode": self.yuzu.portable_mode,
                "sync_user_data": self.yuzu.sync_user_data,
                "last_used_data_path": str(self.yuzu.last_used_data_path)
            },
            "ryujinx_settings": {
                "install_directory": str(self.ryujinx.install_directory.resolve()),
                "portable_mode": self.ryujinx.portable_mode,
                "sync_user_data": self.ryujinx.sync_user_data,
                "last_used_data_path": str(self.ryujinx.last_used_data_path)
            },
            "xenia_settings": {
                "install_directory": str(self.xenia.install_directory.resolve()),
                "release_channel": self.xenia.release_channel,
                "game_directory": str(self.xenia.game_directory.resolve()),
                "portable_mode": self.xenia.portable_mode,
            },
            "app_settings": {
                "dark_mode": self.dark_mode,
                "colour_theme_path": str(self.colour_theme_path.resolve()),
                "delete_files_after_installing": self.delete_files_after_installing,
                "auto_app_updates": self.auto_app_updates,
                "auto_emulator_updates": self.auto_emulator_updates,
                "firmware_denied": self.firmware_denied,
                "announcements_read": self.announcements_read,
            }
        }
        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
        self.logger.info("Settings saved")

    def _set_property(self, property_name, value):
        if property_name == "colour_theme_path":
            if not self.assets.is_theme_valid(theme=value):
                self.logger.error(f"Invalid theme receieved and resetting to default: {value}")
                value = self.default_settings[property_name]
        self.logger.debug(f"Setting {property_name} to {value}")
        self._settings[property_name] = value

    def _get_property(self, property_name):
        return self._settings[property_name]

    colour_theme_path = property(
        lambda self: self._get_property("colour_theme_path"),
        lambda self, value: self._set_property("colour_theme_path", value),
    )

    dark_mode = property(
        lambda self: self._get_property("dark_mode"),
        lambda self, value: self._set_property("dark_mode", value),
    )
    delete_files_after_installing = property(
        lambda self: self._get_property("delete_files_after_installing"),
        lambda self, value: self._set_property("delete_files_after_installing", value),
    )
    auto_app_updates = property(
        lambda self: self._get_property("auto_app_updates"),
        lambda self, value: self._set_property("auto_app_updates", value),
    )
    auto_emulator_updates = property(
        lambda self: self._get_property("auto_emulator_updates"),
        lambda self, value: self._set_property("auto_emulator_updates", value),
    )
    firmware_denied = property(
        lambda self: self._get_property("firmware_denied"),
        lambda self, value: self._set_property("firmware_denied", value),
    )
    announcements_read = property(
        lambda self: self._get_property("announcements_read"),
        lambda self, value: self._set_property("announcements_read", value),
    )
    token = property(
        lambda self: self._get_property("token"),
        lambda self, value: self._set_property("token", value),
    )
