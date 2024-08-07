import json
import os

from settings.app_settings import AppSettings
from settings.dolphin_settings import DolphinSettings
from settings.yuzu_settings import YuzuSettings
from settings.ryujinx_settings import RyujinxSettings
from settings.xenia_settings import XeniaSettings


class Settings:
    def __init__(self, master, root_dir):
        self.root_dir = root_dir
        self.version = "4"
        if os.path.exists(os.path.join(os.getcwd(), "PORTABLE.txt")):
            self.settings_file = os.path.join(os.getcwd(), "portable", "config", "settings.json")
        else:
            self.settings_file = os.path.join(os.getenv("APPDATA"), "Emulator Manager", "config", "settings.json")
        self.master = master

        self.app = AppSettings(self)
        self.yuzu = YuzuSettings(self)
        self.dolphin = DolphinSettings(self)
        self.ryujinx = RyujinxSettings(self)
        self.xenia = XeniaSettings(self)

        if not os.path.exists(self.settings_file) or not self.settings_file_valid():
            self.create_settings_file()
        else:
            self.load()

        self.define_image_paths(os.path.join(root_dir, "assets", "images"))
        self.update_file()

    def create_settings_file(self):
        settings_template = {
            "version": self.version,

            "dolphin_settings": {
                "user_directory": "",
                "install_directory": "",
                "rom_directory": "",
                "current_channel": ""

            },
            "yuzu_settings": {
                "user_directory": "",
                "install_directory": "",
                "installer_path": "",
                "use_yuzu_installer": "",
                "current_yuzu_channel": ""

            },
            "ryujinx_settings": {
                "user_directory": "",
                "install_directory": ""
            },
            "xenia_settings": {
                "user_directory": "",
                "install_directory": "",
                "rom_directory": "",
                "current_xenia_channel": "",
            },
            "app_settings": {
                "image_paths": {
                    "dolphin_logo": '',
                    "dolphin_banner_dark": '',
                    "dolphin_banner_light": "",
                    "yuzu_logo": "",
                    "yuzu_mainline": "",
                    "yuzu_early_access": "",
                    "ryujinx_logo": "",
                    "ryujinx_banner": "",
                    "padlock_dark": "",
                    "padlock_light": "",
                    "play_dark": "",
                    "play_light": "",
                    "settings_dark": "",
                    "settings_light": "",
                    "placeholder_icon": "",
                    "discord_icon": ""
                },
                "appearance_mode": "",
                "colour_theme": "",
                "delete_files": "",
                "check_for_app_updates": "",
                "disable_automatic_updates": "",
                "ask_firmware": ""
            }
        }
        if not os.path.exists(os.path.dirname(os.path.abspath(self.settings_file))):
            os.makedirs(os.path.dirname(os.path.abspath(self.settings_file)))
        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump(settings_template, f, indent=4)

    def define_image_paths(self, image_path):
        self.image_path = image_path
        with open(self.settings_file, "r", encoding="utf-8") as f:
            settings = json.load(f)
        image_paths = settings["app_settings"]["image_paths"]
        if len(image_paths) != 19:
            settings["app_settings"]["image_paths"] = {
                "dolphin_logo": '',
                "dolphin_banner_dark": '',
                "dolphin_banner_light": "",
                "yuzu_logo": "",
                "yuzu_mainline": "",
                "yuzu_early_access": "",
                "ryujinx_logo": "",
                "ryujinx_banner": "",
                "xenia_logo": "",
                "xenia_banner": "",
                "xenia_canary_banner": "",
                "padlock_dark": "",
                "padlock_light": "",
                "play_dark": "",
                "play_light": "",
                "settings_dark": "",
                "settings_light": "",
                "placeholder_icon": "",
                "discord_icon": ""
            }
        for name, path in settings["app_settings"]["image_paths"].items():
            path = os.path.join(image_path, f"{name}.png")
            settings["app_settings"]["image_paths"][name] = path
        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)

    def get_image_path(self, image_name):
        with open(self.settings_file, "r", encoding="utf-8") as f:
            settings = json.load(f)
        if image_name == "all":
            return settings["app_settings"]["image_paths"]
        image_path = settings["app_settings"]["image_paths"][image_name]
        return image_path

    def load(self):
        with open(self.settings_file, "r", encoding="utf-8") as file:
            settings = json.load(file)

        sections = {
            "dolphin_settings": self.dolphin,
            "yuzu_settings": self.yuzu,
            "ryujinx_settings": self.ryujinx,
            "xenia_settings": self.xenia,
            "app_settings": self.app
        }

        for section_name, section_obj in sections.items():
            if section_name not in settings:
                continue
            section_settings = settings[section_name]
            for setting_name, value in section_settings.items():
                if setting_name != "image_paths" and os.path.join("Temp", "_MEI") in os.path.normpath(value):
                    continue  # skip as settings file contains old MEI path.
                elif setting_name == "image_paths":
                    for _, path in value.items():
                        if os.path.join("Temp", "_MEI") in os.path.normpath(path):
                            continue
                if value == "":
                    if os.path.exists(section_obj.default_settings[setting_name]):
                        setattr(section_obj, setting_name,
                                section_obj.default_settings[setting_name])
                        continue
                try:
                    setattr(section_obj, setting_name, value)
                except Exception:
                    pass

    def update_file(self):
        settings = {

            "version": self.version,

            "dolphin_settings": {
                "user_directory": self.dolphin.user_directory,
                "install_directory": self.dolphin.install_directory,
                "rom_directory": self.dolphin.rom_directory,
                "current_channel": self.dolphin.current_channel

            },
            "yuzu_settings": {
                "user_directory": self.yuzu.user_directory,
                "install_directory": self.yuzu.install_directory,
                "installer_path": self.yuzu.installer_path,
                "use_yuzu_installer":  self.yuzu.use_yuzu_installer,
                "current_yuzu_channel": self.yuzu.current_yuzu_channel

            },
            "ryujinx_settings": {
                "user_directory": self.ryujinx.user_directory,
                "install_directory": self.ryujinx.install_directory
            },
            "xenia_settings": {
                "user_directory": self.xenia.user_directory,
                "install_directory": self.xenia.install_directory,
                "current_xenia_channel": self.xenia.current_xenia_channel,
                "rom_directory": self.xenia.rom_directory
            },
            "app_settings": {
                "image_paths": self.get_image_path("all"),
                "appearance_mode": self.app.appearance_mode,
                "colour_theme": self.app.colour_theme,
                "delete_files": self.app.delete_files,
                "check_for_app_updates": self.app.check_for_app_updates,
                "disable_automatic_updates": self.app.disable_automatic_updates,
                "ask_firmware": self.app.ask_firmware
            }
        }
        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)

    def settings_file_valid(self):
        try:
            with open(self.settings_file, "r", encoding="utf-8") as file:
                settings = json.load(file)
                if settings["version"] != self.version and not self.upgrade_if_possible(settings["version"]):
                    return False
                settings["app_settings"]["image_paths"]["yuzu_logo"]  # Check for specific setting existence
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return False
        return True

    def upgrade_if_possible(self, version):
        return version == "3" and self.upgrade_settings("3", "4")

    def upgrade_settings(self, old_version, new_version):
        if old_version == "3" and new_version == "4":
            try:
                with open(self.settings_file, "r+", encoding="utf-8") as file:
                    settings = json.load(file)
                    channel = settings.get("dolphin_settings", {}).get("current_channel", "release")
                    settings["dolphin_settings"]["current_channel"] = "release" if channel != "development" else "development"
                    settings["version"] = new_version
                    file.seek(0)
                    file.truncate()
                    json.dump(settings, file, indent=4)
                return True
            except json.JSONDecodeError:
                pass
        return False
