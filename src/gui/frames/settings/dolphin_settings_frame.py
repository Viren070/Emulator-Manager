import customtkinter

from gui.frames.settings.setting_modal import SettingModal


class DolphinSettingsFrame(customtkinter.CTkFrame):
    def __init__(self, parent_frame, settings):
        super().__init__(parent_frame, corner_radius=0, fg_color="transparent")
        self.settings = settings
        self.build_frame()

    def build_frame(self):
        self.grid_columnconfigure(0, weight=1)

        install_directory_setting = SettingModal(
            master=self,
            settings=self.settings,
            setting_options={
                "object": self.settings.dolphin,
                "id": "install_directory",
                "type": "path",
                "title": "Install Directory",
                "description": "The directory where Dolphin is installed.",
            },
            path_options={
                "type": "directory",
                "title": "Select Dolphin Install Directory",
            }
        )

        game_directory_setting = SettingModal(
            master=self,
            settings=self.settings,
            setting_options={
                "object": self.settings.dolphin,
                "id": "game_directory",
                "type": "path",
                "title": "Game Directory",
                "description": "The directory where your games are stored.",
            },
            path_options={
                "type": "directory",
                "title": "Select Game Directory",
            }
        )

        portable_mode_setting = SettingModal(
            master=self,
            settings=self.settings,
            setting_options={
                "object": self.settings.dolphin,
                "id": "portable_mode",
                "type": "switch",
                "title": "Portable Mode",
                "description": "Enable portable mode for Dolphin.",
            },
        )

        sync_user_data_setting = SettingModal(
            master=self,
            settings=self.settings,
            setting_options={
                "object": self.settings.dolphin,
                "id": "sync_user_data",
                "type": "switch",
                "title": "Sync User Data",
                "description": "Keep your user data synced as you switch between portable and non-portable mode.",
            },
        )

        install_directory_setting.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        game_directory_setting.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        portable_mode_setting.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        sync_user_data_setting.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
