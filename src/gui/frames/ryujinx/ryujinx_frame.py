import customtkinter
from CTkToolTip import CTkToolTip

from core.config import constants
from core.emulators.ryujinx.runner import Ryujinx
from gui.frames.emulator_frame import EmulatorFrame
from gui.frames.firmware_keys_frame import FirmwareKeysFrame
from gui.frames.ryujinx.ryujinx_games_frame import RyujinxROMFrame
from gui.handlers.progress.progress_handler import ProgressHandler
from gui.libs.CTkMessagebox import messagebox
from gui.windows.folder_selector import FolderSelector
from gui.windows.path_dialog import PathDialog


class RyujinxFrame(EmulatorFrame):
    def __init__(self, master, paths, settings, versions, assets, cache, event_manager):
        super().__init__(parent_frame=master, paths=paths, settings=settings, versions=versions, assets=assets)
        self.ryujinx = Ryujinx(settings, versions)
        self.versions = versions
        self.cache = cache
        self.ryujinx_version = None
        self.paths = paths
        self.event_manager = event_manager
        self.add_to_frame()

    def add_to_frame(self):
        # create ryujinx 'Play' frame and widgets
        self.start_frame = customtkinter.CTkFrame(self, corner_radius=0, border_width=0)
        self.start_frame.grid_columnconfigure(0, weight=1)
        self.start_frame.grid_rowconfigure(0, weight=1)

        self.center_frame = customtkinter.CTkFrame(self.start_frame, corner_radius=0)
        self.center_frame.grid(row=0, column=0, sticky="nsew")

        self.center_frame.grid_columnconfigure(0, weight=1)
        self.center_frame.grid_rowconfigure(0, weight=1)
        self.center_frame.grid_rowconfigure(1, weight=1)
        self.center_frame.grid_rowconfigure(2, weight=1)
        self.center_frame.grid_rowconfigure(3, weight=2)

        # Image button
        self.image_button = customtkinter.CTkButton(self.center_frame, text="", fg_color='transparent', hover=False, bg_color='transparent', border_width=0, image=self.assets.ryujinx_banner)
        self.image_button.grid(row=0, column=0, columnspan=3, sticky="n", padx=10, pady=20)

        self.actions_frame = customtkinter.CTkFrame(self.center_frame)
        self.actions_frame.grid(row=2, column=0, columnspan=3)

        self.actions_frame.grid_columnconfigure(0, weight=1)  # Stretch horizontally
        self.actions_frame.grid_columnconfigure(1, weight=1)  # Stretch horizontally
        self.actions_frame.grid_columnconfigure(2, weight=1)  # Stretch horizontally

        self.launch_button = customtkinter.CTkButton(self.actions_frame, height=40, width=225, image=self.assets.play_image, text="Launch Ryujinx  ", command=self.launch_ryujinx_button_event, font=customtkinter.CTkFont(size=15, weight="bold"))
        self.launch_button.grid(row=0, column=2, padx=30, pady=15, sticky="n")
        self.launch_button.bind("<Button-1>", command=self.launch_ryujinx_button_event)
        CTkToolTip(self.launch_button, message="Click me to launch Ryujinx.\nHold shift to toggle the update behaviour.\nIf automatic updates are disabled, shift-clicking will update the emulator\nand otherwise it will skip the update.")
        self.install_button = customtkinter.CTkButton(self.actions_frame, text="Install Ryujinx", command=self.install_ryujinx_button_event)
        self.install_button.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        self.install_button.bind("<Button-1>", command=self.install_ryujinx_button_event)
        CTkToolTip(self.install_button, message="Click me to download and install the latest release of Ryujinx from the internet\nShift-Click me to install Ryujinx with a custom archive")

        self.delete_button = customtkinter.CTkButton(self.actions_frame, text="Delete Ryujinx", fg_color="red", hover_color="darkred", command=self.delete_ryujinx_button_event)
        self.delete_button.grid(row=0, column=3, padx=10, pady=5, sticky="ew")
        CTkToolTip(self.delete_button, message="Click me to delete the installation of Ryujinx at the directory specified in settings.")

        self.firmware_keys_frame = FirmwareKeysFrame(master=self.center_frame, frame_obj=self, emulator_obj=self.ryujinx)
        self.firmware_keys_frame.grid(row=3, column=0, padx=10, pady=10, columnspan=3)

        self.log_frame = customtkinter.CTkFrame(self.center_frame, fg_color='transparent', border_width=0)
        self.log_frame.grid(row=4, column=0, padx=80, sticky="ew")
        self.log_frame.grid_propagate(False)
        self.log_frame.grid_columnconfigure(0, weight=3)
        self.main_progress_frame = ProgressHandler(self.log_frame)
        # create ryujinx 'Manage Data' frame and widgets
        self.manage_data_frame = customtkinter.CTkFrame(self, corner_radius=0, bg_color="transparent")
        self.manage_data_frame.grid_columnconfigure(0, weight=1)
        self.manage_data_frame.grid_columnconfigure(1, weight=1)
        self.manage_data_frame.grid_rowconfigure(0, weight=1)
        self.manage_data_frame.grid_rowconfigure(1, weight=2)
        self.data_actions_frame = customtkinter.CTkFrame(self.manage_data_frame, height=150)
        self.data_actions_frame.grid(row=0, column=0, padx=20, columnspan=3, pady=20, sticky="ew")
        self.data_actions_frame.grid_columnconfigure(1, weight=1)

        self.import_optionmenu = customtkinter.CTkOptionMenu(self.data_actions_frame, width=300, values=["All Data", "Save Data", "Custom..."])
        self.export_optionmenu = customtkinter.CTkOptionMenu(self.data_actions_frame, width=300, values=["All Data", "Save Data", "Custom..."])
        self.delete_optionmenu = customtkinter.CTkOptionMenu(self.data_actions_frame, width=300, values=["All Data", "Save Data", "Custom..."])

        self.import_data_button = customtkinter.CTkButton(self.data_actions_frame, text="Import", command=self.import_data_button_event)
        self.export_data_button = customtkinter.CTkButton(self.data_actions_frame, text="Export", command=self.export_data_button_event)
        self.delete_data_button = customtkinter.CTkButton(self.data_actions_frame, text="Delete", command=self.delete_data_button_event, fg_color="red", hover_color="darkred")

        self.import_optionmenu.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.import_data_button.grid(row=0, column=1, padx=10, pady=10, sticky="e")
        self.export_optionmenu.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.export_data_button.grid(row=1, column=1, padx=10, pady=10, sticky="e")
        self.delete_optionmenu.grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.delete_data_button.grid(row=2, column=1, padx=10, pady=10, sticky="e")

        self.data_log = customtkinter.CTkFrame(self.manage_data_frame)
        self.data_log.grid(row=1, column=0, padx=20, pady=20, columnspan=3, sticky="new")
        self.data_log.grid_columnconfigure(0, weight=1)
        self.data_log.grid_rowconfigure(1, weight=1)
        self.data_progress_handler = ProgressHandler(self.data_log)
        # create ryujinx downloader button, frame and widgets

        self.actions_frame.grid_propagate(False)

        self.manage_games_frame = RyujinxROMFrame(self, self.settings, self.cache)
        self.manage_games_frame.grid(row=0, column=0,  padx=20, pady=20, sticky="nsew")

    # override parent method to check for titleDB before switching to roms frame
    def manage_games_button_event(self):
        self.manage_games_frame.current_roms_frame.assert_titledb()
        self.select_frame_by_name("games")

    def configure_buttons(
        self,
        state="disabled",
        launch_ryujinx_button_text="Launch Ryujinx",
        install_ryujinx_button_text="Install Ryujinx",
        delete_ryujinx_button_text="Delete Ryujinx",
        install_firmware_button_text="Install",
        install_keys_button_text="Install",
    ):
        self.launch_button.configure(state=state, text=launch_ryujinx_button_text)
        self.install_button.configure(state=state, text=install_ryujinx_button_text)
        self.delete_button.configure(state=state, text=delete_ryujinx_button_text)
        self.firmware_keys_frame.install_firmware_button.configure(state=state, text=install_firmware_button_text)
        self.firmware_keys_frame.install_keys_button.configure(state=state, text=install_keys_button_text)
        self.firmware_keys_frame.update_installed_versions()

    def configure_data_buttons(self, state="disabled", import_text="Import", export_text="Export", delete_text="Delete"):
        self.import_data_button.configure(state=state, text=import_text)
        self.export_data_button.configure(state=state, text=export_text)
        self.delete_data_button.configure(state=state, text=delete_text)

    def launch_ryujinx_button_event(self, event=None):
        if event is None or self.launch_button.cget("state") == "disabled":
            return
        update_mode = self.settings.auto_emulator_updates if not event.state & 1 else not self.settings.auto_emulator_updates
        self.configure_buttons("disabled", launch_ryujinx_button_text="Launching...")
        self.event_manager.add_event(
            event_id="launch_ryujinx",
            func=self.launch_ryujinx_handler,
            kwargs={"update_mode": update_mode},
            completion_functions=[lambda: self.configure_buttons("normal", launch_ryujinx_button_text="Launch Ryujinx")],
            error_functions=[lambda: messagebox.showerror(self.winfo_toplevel(), "Error", "An unexpected error occured while launching Ryujinx. Please check the logs for more information and report the issue.")],
        )

    def launch_ryujinx_handler(self, update_mode=False):
        if update_mode:
            self.configure_buttons(launch_ryujinx_button_text="Checking for updates...")
            update = self.install_ryujinx_handler(update_mode=True)
            if update.get("status", False) is False:
                self.configure_buttons(launch_ryujinx_button_text="Oops!")
                return update

        self.configure_buttons(launch_ryujinx_button_text="Launched!")
        launch_result = self.ryujinx.launch_ryujinx()

        if not launch_result["status"]:
            self.configure_buttons(launch_ryujinx_button_text="Oops!")
            return {
                "message": {
                    "function": messagebox.showerror,
                    "arguments": (self.winfo_toplevel(), "Error", launch_result["message"]),
                }
            }
        if launch_result["error_encountered"]:
            self.configure_buttons(launch_ryujinx_button_text="Oops!")
            return {
                "message": {
                    "function": messagebox.showerror,
                    "arguments": (self.winfo_toplevel(), "Error", launch_result["message"]),
                }
            }

        return {}

    def install_ryujinx_button_event(self, event=None):
        if event is None or self.install_button.cget("state") == "disabled":
            return
        if (
            (self.settings.ryujinx.install_directory / "publish").is_dir() and (
                any((self.settings.ryujinx.install_directory / "publish").iterdir()) and (
                    messagebox.askyesno(
                        self.winfo_toplevel(),
                        "Confirmation", "An installation of Ryujinx already exists. Do you want to overwrite it?"
                    ) != "yes"
                )
            )
        ):
            return
        path_to_archive = None

        if event.state & 1:
            path_to_archive = PathDialog(filetypes=(".zip",), title="Custom Ryujinx Archive", text="Enter path to Ryujinx archive: ").get_input()
            if not path_to_archive["status"]:
                if path_to_archive["cancelled"]:
                    return
                messagebox.showerror(self.winfo_toplevel(), "Install Ryujinx", path_to_archive["message"])
                return
            path_to_archive = path_to_archive["path"]

        self.configure_buttons(install_ryujinx_button_text="Installing...")
        self.event_manager.add_event(
            event_id="install_ryujinx",
            func=self.install_ryujinx_handler,
            kwargs={"archive_path": path_to_archive},
            completion_functions=[lambda: self.configure_buttons(state="normal")],
            error_functions=[lambda: messagebox.showerror(self.winfo_toplevel(), "Error", "An unexpected error occured while installing Ryujinx. Please check the logs for more information and report this issue.")]
        )

    def install_ryujinx_handler(self, update_mode=False, archive_path=None):
        custom_install = archive_path is not None
        if archive_path is None:
            release_fetch_result = self.ryujinx.get_release()
            if not release_fetch_result["status"]:
                return {
                    "message": {
                        "function": messagebox.showerror,
                        "arguments": (self.winfo_toplevel(), "Ryujinx", f"Failed to fetch the latest release of Ryujinx:\n\n{release_fetch_result['message']}"),
                    }
                }

            if update_mode:
                if release_fetch_result["release"]["version"] == self.ryujinx.get_installed_version():
                    return {
                        "status": True
                    }
                self.configure_buttons(launch_ryujinx_button_text="Updating...")
            total_units = release_fetch_result["release"]["size"] / 1024 / 1024
            self.main_progress_frame.start_operation(title="Install Ryujinx", total_units=total_units, units=" MiB", status="Downloading...")
            download_result = self.ryujinx.download_release(release_fetch_result["release"], progress_handler=self.main_progress_frame)
            if not download_result["status"]:
                if "cancelled" in download_result["message"]:
                    return {
                        "message": {
                            "function": messagebox.showinfo,
                            "arguments": (self.winfo_toplevel(), "Ryujinx", "Download was cancelled"),
                        }
                    }
                return {
                    "message": {
                        "function": messagebox.showerror,
                        "arguments": (self.winfo_toplevel(), "Ryujinx", f"Failed to download the latest release of Ryujinx:\n\n{download_result['message']}"),
                    }
                }

            archive_path = download_result["download_path"]

        self.main_progress_frame.start_operation(title="Install Ryujinx", total_units=0, units=" Files", status="Extracting...")
        extract_result = self.ryujinx.extract_release(archive_path, progress_handler=self.main_progress_frame)
        if not extract_result["status"]:
            if "cancelled" in extract_result["message"]:
                return {
                    "message": {
                        "function": messagebox.showinfo,
                        "arguments": (self.winfo_toplevel(), "Ryujinx", "Extraction was cancelled"),
                    }
                }
            return {
                "message": {
                    "function": messagebox.showerror,
                    "arguments": (self.winfo_toplevel(), "Ryujinx", f"Failed to extract the latest release of Ryujinx:\n\n{extract_result['message']}"),
                }
            }

        self.metadata.set_version("ryujinx", release_fetch_result["release"]["version"] if not custom_install else "")
        if not custom_install and self.settings.delete_files_after_installing:
            archive_path.unlink()
        return {
            "message": {
                "function": messagebox.showsuccess,
                "arguments": (self.winfo_toplevel(), "Ryujinx", f"Successfully installed Ryujinx to {self.settings.ryujinx.install_directory}"),
            },
            "status": True
        }

    def delete_ryujinx_button_event(self, event=None):
        if not (self.settings.ryujinx.install_directory / "publish").is_dir() or not any((self.settings.ryujinx.install_directory / "publish").iterdir()):
            messagebox.showerror(self.winfo_toplevel(), "Error", f"Could not find a Ryujinx installation at {self.settings.ryujinx.install_directory}")
            return
        if messagebox.askyesno(self.winfo_toplevel(), "Confirmation", "This will delete the Ryujinx installation. This action cannot be undone, are you sure you wish to continue?", icon="warning") != "yes":
            return
        self.configure_buttons(delete_ryujinx_button_text="Deleting...")
        self.event_manager.add_event(
            event_id="delete_ryujinx",
            func=self.delete_ryujinx_handler,
            error_functions=[lambda: messagebox.showerror(self.winfo_toplevel(), "Error", "An unexpected error occured while deleting Ryujinx. Please check the logs for more information and report this issue.")],
            completion_functions=[lambda: self.configure_buttons(state="normal")],
        )

    def delete_ryujinx_handler(self):
        delete_result = self.ryujinx.delete_ryujinx()
        if not delete_result["status"]:
            return {
                "message": {
                    "function": messagebox.showerror,
                    "arguments": (self.winfo_toplevel(), "Error", delete_result["message"]),
                }
            }

        return {
            "message": {
                "function": messagebox.showsuccess,
                "arguments": (self.winfo_toplevel(), "Success", delete_result["message"]),
            }
        }

    def import_data_button_event(self):

        import_option = self.import_optionmenu.get()

        if import_option == "Custom...":
            directory, folders = FolderSelector(
                title="Choose directory and folders to import",
                allowed_folders=constants.Ryujinx.USER_FOLDERS.value,
                show_files=True,
            ).get_input()
        else:
            directory = PathDialog(title="Import Directory", text="Enter directory to import from: ", directory=True).get_input()
            if not directory["status"]:
                if directory["cancelled"]:
                    return
                messagebox.showerror(self.winfo_toplevel(), "Error", directory["message"])
                return
            directory = directory["path"]
            folders = constants.Ryujinx.USER_FOLDERS.value

        self.configure_data_buttons(import_text="Importing...")
        self.event_manager.add_event(
            event_id="import_ryujinx_data",
            func=self.import_data_handler,
            kwargs={"import_directory": directory, "folders": folders, "save_folder": import_option == "Save Data"},
            completion_functions=[lambda: self.configure_data_buttons(state="normal")],
            error_functions=[lambda: messagebox.showerror(self.winfo_toplevel(), "Error", "An unexpected error occurred while importing Ryujinx data.\nPlease check the logs for more information and report this issue.")]
        )

    def import_data_handler(self, import_directory, folders, save_folder=False):
        self.data_progress_handler.start_operation(
            title="Import Ryujinx Data",
            total_units=0,
            units=" Files",
            status="Importing..."
        )
        import_result = self.ryujinx.import_ryujinx_data(
            import_directory=import_directory,
            folders=folders,
            progress_handler=self.data_progress_handler,
            save_folder=save_folder
        )
        if not import_result["status"]:
            return {
                "message": {
                    "function": messagebox.showerror,
                    "arguments": (self.winfo_toplevel(), "Error", f"Failed to import Ryujinx data: {import_result['message']}"),
                }
            }
        return {
            "message": {
                "function": messagebox.showsuccess,
                "arguments": (self.winfo_toplevel(), "Import Ryujinx Data", f"Successfully imported Ryujinx data from {import_directory}"),
            }
        }

    def export_data_button_event(self):
        export_directory = PathDialog(title="Export Directory", text="Enter directory to export to: ", directory=True)
        export_directory = export_directory.get_input()
        if not export_directory["status"]:
            if export_directory["cancelled"]:
                return
            messagebox.showerror("Error", export_directory["message"])
            return
        export_directory = export_directory["path"]

        if self.export_optionmenu.get() == "Custom...":
            _, folders = FolderSelector(title="Choose folders to export", predefined_directory=self.ryujinx.get_user_directory(), allowed_folders=constants.Ryujinx.USER_FOLDERS.value, show_files=True).get_input()
            if folders is None:
                return
        else:
            folders = constants.Ryujinx.USER_FOLDERS.value

        self.configure_data_buttons(export_text="Exporting...")

        self.event_manager.add_event(
            event_id="export_ryujinx_data",
            func=self.export_data_handler,
            kwargs={"export_directory": export_directory, "folders": folders, "save_folder": self.export_optionmenu.get() == "Save Data"},
            completion_functions=[lambda: self.configure_data_buttons(state="normal")],
            error_functions=[lambda: messagebox.showerror(self.winfo_toplevel(), "Error", "An unexpected error occurred while exporting Ryujinx data.\nPlease check the logs for more information and report this issue.")]
        )

    def export_data_handler(self, export_directory, folders, save_folder=False):
        self.data_progress_handler.start_operation(
            title="Export Ryujinx Data",
            total_units=0,
            units=" Files",
            status="Exporting..."
        )
        export_result = self.ryujinx.export_ryujinx_data(
            export_directory=export_directory,
            folders=folders,
            progress_handler=self.data_progress_handler,
            save_folder=save_folder
        )
        if not export_result["status"]:
            return {
                "message": {
                    "function": messagebox.showerror,
                    "arguments": (self.winfo_toplevel(), "Error", f"Failed to export Ryujinx data: {export_result['message']}"),
                }
            }
        return {
            "message": {
                "function": messagebox.showsuccess,
                "arguments": (self.winfo_toplevel(), "Export Ryujinx Data", f"Successfully exported Ryujinx data to {export_directory}"),
            }
        }

    def delete_data_button_event(self):
        if self.delete_optionmenu.get() == "Custom...":
            _, folders = FolderSelector(title="Choose folders to delete", predefined_directory=self.ryujinx.get_user_directory(), allowed_folders=constants.Ryujinx.USER_FOLDERS.value, show_files=True).get_input()
            if folders is None:
                return
        else:
            folders = constants.Ryujinx.USER_FOLDERS.value

        if messagebox.askyesno(self.winfo_toplevel(), "Confirmation", "This will delete the data from Ryujinx's directory. This action cannot be undone, are you sure you wish to continue?") != "yes":
            return
        self.configure_data_buttons(delete_text="Deleting...")
        self.event_manager.add_event(
            event_id="delete_ryujinx_data",
            func=self.delete_data_handler,
            kwargs={"folders": folders},
            completion_functions=[lambda: self.configure_data_buttons(state="normal")],
            error_functions=[lambda: messagebox.showerror(self.winfo_toplevel(), "Error", "An unexpected error occurred while deleting Ryujinx data.\nPlease check the logs for more information and report this issue.")]
        )

    def delete_data_handler(self, folders):
        self.data_progress_handler.start_operation(
            title="Delete Ryujinx Data",
            total_units=0,
            units=" Files",
            status="Deleting..."
        )
        delete_result = self.ryujinx.delete_ryujinx_data(folders_to_delete=folders, progress_handler=self.data_progress_handler)
        if not delete_result["status"]:
            return {
                "message": {
                    "function": messagebox.showerror,
                    "arguments": (self.winfo_toplevel(), "Error", f"Failed to delete Ryujinx data: {delete_result['message']}"),
                }
            }
        return {
            "message": {
                "function": messagebox.showsuccess,
                "arguments": (self.winfo_toplevel(), "Delete Ryujinx Data", "Successfully deleted Ryujinx data"),
            }
        }
