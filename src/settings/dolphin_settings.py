import os

from utils.paths import is_path_exists_or_creatable


class DolphinSettings:
    def __init__(self, master):
        self.emulator_file_path = os.path.join(
            master.root_dir, "Emulator Files")
        self.default_settings = {
            'user_directory': (os.path.join(os.getenv("APPDATA"), "Dolphin Emulator")),
            'install_directory': (os.path.join(os.getenv("LOCALAPPDATA"), "Dolphin Emulator")),
            'rom_directory': '',
            'current_channel': "release"
        }
        self._settings = self.default_settings.copy()

    def restore_default(self):
        for name, value in self.default_settings.items():
            if value == '':
                continue
            try:
                setattr(self, name, value)
            except (ValueError, FileNotFoundError):
                if name == "zip_path":
                    setattr(self, name, "")
                else:
                    os.makedirs(value)
                    setattr(self, name, value)

    def _set_directory_property(self, property_name, value):
        if (property_name == "rom_directory" and os.path.exists(value)) or (property_name != "rom_directory" and is_path_exists_or_creatable(value)):
            self._settings[property_name] = value
        else:
            raise ValueError(f"{property_name.replace(
                '__', '/').replace('_', ' ').title()} - Invalid Path: {(value)}")

    def _set_property(self, property_name, value):
        self._settings[property_name] = value

    def _get_property(self, property_name):
        return self._settings[property_name]

    user_directory = property(lambda self: self._get_property('user_directory'),
                              lambda self, value: self._set_directory_property('user_directory', value))

    install_directory = property(lambda self: self._get_property('install_directory'),
                                 lambda self, value: self._set_directory_property('install_directory', value))

    rom_directory = property(lambda self: self._get_property('rom_directory'),
                             lambda self, value: self._set_directory_property('rom_directory', value))
    current_channel = property(lambda self: self._get_property('current_channel'),
                               lambda self, value: self._set_property('current_channel', value))
