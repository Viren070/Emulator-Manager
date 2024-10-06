import argparse
from core.config import constants
from core.config.paths import Paths
from core.config.settings import Settings
from core.config.versions import Versions
from core.config.cache import Cache
import os
import webbrowser
from pathlib import Path
from core.emulators.dolphin.runner import Dolphin
from core.emulators.ryujinx.runner import Ryujinx
from core.emulators.xenia.runner import Xenia
from core.emulators.yuzu.runner import Yuzu
from cli.handlers.progress.progress_handler import ProgressHandler

class EmuHavenCLI:
    """ 
    EmuHaven CLI Plan:
    
    available options:
    
    misc:
    --open-discord: open the discord server
    --open-github: open the github repository
    --open-kofi: open the kofi page
    --clear-cache: clear the cache
    --reset-settings: reset all settings to default
    --show-settings: show the current settings
    --about: show information about the application
    --version: show the version of the application
    --help: show the help message
    --check-for-updates: check for updates
    
    config:
    --set-setting <setting_type> <setting_name> <value>: set a setting
    
    core:
    --launch-emulator: launch an emulator (flags: --update)
        --update: update the emulator before launching
        
    --delete-emulator <emulator>: delete an emulator
    --install-emulator <emulator>: install an emulator
    --update-emulator <emulator>: update an emulator (calls install-emulator)
    --get-game-titleid-mapping <emulator>: get the game titleid mapping for an emulator
    --download-switch-saves <title_id>: download switch saves
    --install-switch-firmware <version> <emulator>: install firmware
    --install-switch-keys <emulator>: install keys
    
    
    
    """
    def __init__(self, paths: Paths, settings: Settings, versions: Versions, cache: Cache):
        self.paths = paths
        self.settings = settings
        self.versions = versions
        self.cache = cache
        self.dolphin = Dolphin(settings=self.settings, versions=self.versions)
        self.yuzu = Yuzu(settings=self.settings, versions=self.versions)
        self.ryujinx = Ryujinx(settings=self.settings, versions=self.versions)
        self.xenia = Xenia(settings=self.settings, versions=self.versions)
        self.args = self.parse_args()
        self.progress_handler = ProgressHandler()
        self.run()
    
    def parse_args(self):
        parser = argparse.ArgumentParser(description="EmuHaven CLI")

        # Miscellaneous group
        misc_group = parser.add_argument_group('misc', 'Miscellaneous options')
        misc_group.add_argument("--open-discord", action="store_true", help="Open the discord server")
        misc_group.add_argument("--open-github", action="store_true", help="Open the github repository")
        misc_group.add_argument("--open-kofi", action="store_true", help="Open the kofi page")
        misc_group.add_argument("--clear-cache", action="store_true", help="Clear the cache directory")
        misc_group.add_argument("--version", action="version", help="Show the version of the application", version=constants.App.VERSION.value)
        misc_group.add_argument("--check-for-updates", action="store_true", help="Check for updates")

        # Configuration group
        config_group = parser.add_argument_group('config', 'Configuration options')
        config_group.add_argument("--set-setting", nargs=3, metavar=('setting_type', 'setting_name', 'value'), help="Set a setting")
        config_group.add_argument("--reset-settings", action="store_true", help="Reset all settings to default")
        config_group.add_argument("--open-settings-file", action="store_true", help="Open the settings file in the default editor")
        
        # Core group
        core_group = parser.add_argument_group('core', 'Core options')
        core_group.add_argument("--delete-emulator", metavar='emulator', choices=constants.App.VALID_EMULATOR_NAMES.value, help="Delete an emulator")
        core_group.add_argument("--get-switch-game-list", metavar='emulator', help="Get the game list including title ids for an emulator")
        core_group.add_argument("--download-switch-saves", metavar='title_id', help="Download switch saves")
        core_group.add_argument("--install-switch-firmware", nargs=2, metavar=('version', 'emulator'), help="Install firmware")
        core_group.add_argument("--install-switch-keys", metavar='emulator', help="Install keys")

        # Subparsers for install-emulator
        subparsers = parser.add_subparsers(dest='command', help="Emulator commands")

        install_emulator_parser = subparsers.add_parser('install-emulator', help='Install an emulator')
        install_emulator_parser.add_argument('emulator', choices=constants.App.VALID_EMULATOR_NAMES.value, help='The emulator to install')
        install_emulator_parser.add_argument('--custom-archive', help='Path to a custom archive for installation', default=None)

        launch_emulator_parser = subparsers.add_parser('launch-emulator', help='Launch an emulator')
        launch_emulator_parser.add_argument('emulator', choices=constants.App.VALID_EMULATOR_NAMES.value, help='The emulator to launch')
        launch_emulator_parser.add_argument('--update', action='store_true', help='Update the emulator before launching')
    
        args = parser.parse_args()

        return args
    
    def run(self):
        if self.args.open_discord:
            webbrowser.open(constants.App.DISCORD.value)
            
        if self.args.open_github:
            webbrowser.open(constants.App.GITHUB.value)
        
        if self.args.open_kofi:
            webbrowser.open(constants.App.KOFI.value)
            
        if self.args.clear_cache:
            self.cache.reset()
            
        if self.args.reset_settings:
            self.settings.reset()
            
        if self.args.open_settings_file:
            os.startfile(self.paths.settings_file)
            
        if self.args.set_setting:
            setting_type, setting_name, value = self.args.set_setting
            if "path" or "dir" in setting_name:
                value = Path(value)
            if not value.exists():
                raise ValueError(f"Invalid path: {value}")
            match setting_type:
                case "dolphin":
                    if setting_name not in self.settings.dolphin.default_config:
                        raise ValueError(f"Invalid setting name: {setting_name}")
                    setattr(self.settings.dolphin, setting_name, value)
                case "yuzu":
                    if setting_name not in self.settings.yuzu.default_config:
                        raise ValueError(f"Invalid setting name: {setting_name}")
                    setattr(self.settings.yuzu, setting_name, value)
                case "ryujinx":
                    if setting_name not in self.settings.ryujinx.default_config:
                        raise ValueError(f"Invalid setting name: {setting_name}")
                    setattr(self.settings.ryujinx, setting_name, value)
                case "xenia":
                    if setting_name not in self.settings.xenia.default_config:
                        raise ValueError(f"Invalid setting name: {setting_name}")
                    setattr(self.settings.xenia, setting_name, value)
                case "app":
                    if setting_name not in self.settings.default_settings:
                        raise ValueError(f"Invalid setting name: {setting_name}")
                    setattr(self.settings, setting_name, value)
                case _:
                    raise ValueError(f"Invalid setting type: {setting_type}")
            self.settings.save()
            
        if self.args.delete_emulator:
            match self.args.delete_emulator:
                case "dolphin":
                    self.dolphin.delete_dolphin()
                case "yuzu":
                    self.yuzu.delete_yuzu()
                case "ryujinx":
                    self.ryujinx.delete_ryujinx()
                case "xenia":
                    self.xenia.delete_xenia()
                case _:
                    raise ValueError(f"Invalid emulator: {self.args.delete_emulator}")
                
        if self.args.command == "install-emulator":
            emulator = self.args.emulator
            custom_archive = self.args.custom_archive
            if custom_archive:
                custom_archive = Path(custom_archive)
                if not custom_archive.exists():
                    raise ValueError(f"Invalid path: {custom_archive}")
            print(f"Installing {emulator} emulator, custom archive: {custom_archive}")
            match emulator:
                case "dolphin":
                    if not custom_archive:
                        latest_release = self.dolphin.get_dolphin_release()
                        if not latest_release["status"]:
                            raise ValueError(f"Failed to get latest Dolphin release: {latest_release['message']}")
                        latest_release = latest_release["release"]
                        
                        download_result = self.dolphin.download_release(latest_release, progress_handler=self.progress_handler)
                        if not download_result["status"]:
                            raise ValueError(f"Failed to download Dolphin release: {download_result['message']}")
                    
                    extract_result = self.dolphin.extract_release(download_result["download_path"], progress_handler=self.progress_handler)
                    if not extract_result["status"]:
                        raise ValueError(f"Failed to extract Dolphin release: {extract_result['message']}")
                case "yuzu":
                    pass
                case "ryujinx":
                    self.ryujinx.install_ryujinx()
                case "xenia":
                    self.xenia.install_xenia()
                case _:
                    raise ValueError(f"Invalid emulator: {self.args.install_emulator}")