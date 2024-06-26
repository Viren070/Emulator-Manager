import os
from threading import Thread
from tkinter import messagebox

import customtkinter
from CTkToolTip import CTkToolTip
from PIL import Image

from emulators.yuzu import Yuzu
from gui.frames.emulator_frame import EmulatorFrame
from gui.frames.firmware_keys_frame import FirmwareKeysFrame
from gui.frames.progress_frame import ProgressFrame
from gui.frames.yuzu.yuzu_rom_frame import YuzuROMFrame
from gui.windows.path_dialog import PathDialog
from gui.windows.folder_selector import FolderSelector

FOLDERS = ["amiibo", "cache", "config", "crash_dumps", "dump", "icons", "keys", "load", "log", "nand", "play_time", "screenshots", "sdmc", "shader", "tas", "sysdata"]


class YuzuFrame(EmulatorFrame):
    def __init__(self, parent_frame, settings, metadata, cache):
        super().__init__(parent_frame, settings, metadata)
        self.yuzu = Yuzu(self, settings, metadata)
        self.cache = cache
        self.mainline_version = None
        self.early_access_version = None
        self.installed_firmware_version = "Unknown"
        self.installed_key_version = "Unknown"
        self.installed_mainline_version = ""
        self.installed_early_access_version = ""
        self.add_to_frame()

    def add_to_frame(self):
        self.play_image = customtkinter.CTkImage(light_image=Image.open(self.settings.get_image_path("play_light")),
                                                 dark_image=Image.open(self.settings.get_image_path("play_dark")), size=(20, 20))
        self.yuzu_mainline = customtkinter.CTkImage(Image.open(self.settings.get_image_path("yuzu_mainline")), size=(276, 129))
        self.yuzu_early_access = customtkinter.CTkImage(Image.open(self.settings.get_image_path("yuzu_early_access")), size=(276, 129))

        # create yuzu 'Play' frame and widgets
        self.start_frame = customtkinter.CTkFrame(self, corner_radius=0, border_width=0)
        self.start_frame.grid_columnconfigure(0, weight=1)
        self.start_frame.grid_rowconfigure(0, weight=1)

        self.center_frame = customtkinter.CTkFrame(self.start_frame, border_width=0)
        self.center_frame.grid(row=0, column=0, sticky="nsew")
        # self.center_frame.grid_propagate(False)
        self.center_frame.grid_columnconfigure(0, weight=1)
        self.center_frame.grid_rowconfigure(0, weight=1)
        self.center_frame.grid_rowconfigure(1, weight=1)
        self.center_frame.grid_rowconfigure(2, weight=1)
        self.center_frame.grid_rowconfigure(3, weight=2)

        self.mainline_image = self.yuzu_mainline
        self.early_access_image = self.yuzu_early_access
        self.selected_channel = customtkinter.StringVar()
        self.version_optionmenu = customtkinter.CTkOptionMenu(self.center_frame, variable=self.selected_channel, command=self.switch_channel, values=["Mainline", "Early Access"])
        self.version_optionmenu.grid(row=0, column=0, padx=10, pady=20, sticky="ne")

        # Image button
        self.image_button = customtkinter.CTkButton(self.center_frame, text="", fg_color='transparent', hover=False, bg_color='transparent', border_width=0, image=self.mainline_image)
        self.image_button.grid(row=0, column=0, columnspan=3, sticky="n", padx=10, pady=20)

        self.mainline_actions_frame = customtkinter.CTkFrame(self.center_frame)
        self.mainline_actions_frame.grid(row=2, column=0, columnspan=3)

        self.mainline_actions_frame.grid_columnconfigure(0, weight=1)  # Stretch horizontally
        self.mainline_actions_frame.grid_columnconfigure(1, weight=1)  # Stretch horizontally
        self.mainline_actions_frame.grid_columnconfigure(2, weight=1)  # Stretch horizontally

        self.launch_mainline_button = customtkinter.CTkButton(self.mainline_actions_frame, height=40, width=200, image=self.play_image, text="Launch Yuzu  ", command=self.launch_mainline_button_event, font=customtkinter.CTkFont(size=15, weight="bold"))
        self.launch_mainline_button.grid(row=0, column=2, padx=30, pady=15, sticky="n")
        self.launch_mainline_button.bind("<Button-1>", command=self.launch_mainline_button_event)
        CTkToolTip(self.launch_mainline_button, message="Click me to launch mainline yuzu.\nShift-click me to launch without checking for updates.")
        self.install_mainline_button = customtkinter.CTkButton(self.mainline_actions_frame, text="Install Yuzu", command=self.install_mainline_button_event)
        self.install_mainline_button.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        self.install_mainline_button.bind("<Button-1>", command=self.install_mainline_button_event)
        CTkToolTip(self.install_mainline_button, message="Click me to download and install the latest mainline release of yuzu from the internet\nShift-Click me to install yuzu with a custom archive")

        self.delete_mainline_button = customtkinter.CTkButton(self.mainline_actions_frame, text="Delete Yuzu", fg_color="red", hover_color="darkred", command=self.delete_mainline_button_event)
        self.delete_mainline_button.grid(row=0, column=3, padx=10, pady=5, sticky="ew")
        CTkToolTip(self.delete_mainline_button, message="Click me to delete the installation of mainline yuzu at the directory specified in settings.")
        # Early Access Actions Frame

        self.early_access_actions_frame = customtkinter.CTkFrame(self.center_frame)

        self.early_access_actions_frame.grid_columnconfigure(0, weight=1)  # Stretch horizontally
        self.early_access_actions_frame.grid_columnconfigure(1, weight=1)  # Stretch horizontally
        self.early_access_actions_frame.grid_columnconfigure(2, weight=1)  # Stretch horizontally

        self.launch_early_access_button = customtkinter.CTkButton(self.early_access_actions_frame, height=40, width=200, image=self.play_image, text="Launch Yuzu EA  ", command=self.launch_early_access_button_event, font=customtkinter.CTkFont(size=15, weight="bold"))
        self.launch_early_access_button.grid(row=0, column=2, padx=30, pady=15, sticky="n")
        self.launch_early_access_button.bind("<Button-1>", command=self.launch_early_access_button_event)
        CTkToolTip(self.launch_early_access_button, message="Click me to launch yuzu early access.\nHold shift to toggle the update behaviour.\nIf automatic updates are disabled, shift-clicking will update the emulator\nand otherwise it will skip the update.")
        self.delete_early_access_button = customtkinter.CTkButton(self.early_access_actions_frame, text="Delete Yuzu EA", fg_color="red", hover_color="darkred", command=self.delete_early_access_button_event)
        self.delete_early_access_button.grid(row=0, column=3, padx=10, pady=5, sticky="ew")
        CTkToolTip(self.delete_early_access_button, message="Click me to delete the installation of yuzu early access at the directory specified in settings.")

        self.install_early_access_button = customtkinter.CTkButton(self.early_access_actions_frame, text="Install Yuzu EA  ", command=self.install_early_access_button_event)
        self.install_early_access_button.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        self.install_early_access_button.bind("<Button-1>", command=self.install_early_access_button_event)
        CTkToolTip(self.install_early_access_button, message="Click me to download and install the latest early access release of yuzu from the internet\nShift-Click me to install yuzu with a custom archive.")

        self.firmware_keys_frame = FirmwareKeysFrame(self.center_frame, self)
        self.firmware_keys_frame.grid(row=3, column=0, padx=10, pady=10, columnspan=3)

        self.yuzu_log_frame = customtkinter.CTkFrame(self.center_frame, fg_color='transparent', border_width=0)
        self.yuzu_log_frame.grid(row=4, column=0, padx=80, sticky="ew")
        self.yuzu_log_frame.grid_propagate(False)
        self.yuzu_log_frame.grid_columnconfigure(0, weight=3)
        self.yuzu.main_progress_frame = ProgressFrame(self.yuzu_log_frame)
        # create yuzu 'Manage Data' frame and widgets
        self.manage_data_frame = customtkinter.CTkFrame(self, corner_radius=0, bg_color="transparent")
        self.manage_data_frame.grid_columnconfigure(0, weight=1)
        self.manage_data_frame.grid_columnconfigure(1, weight=1)
        self.manage_data_frame.grid_rowconfigure(0, weight=1)
        self.manage_data_frame.grid_rowconfigure(1, weight=2)
        self.yuzu_data_actions_frame = customtkinter.CTkFrame(self.manage_data_frame, height=150)
        self.yuzu_data_actions_frame.grid(row=0, column=0, padx=20, columnspan=3, pady=20, sticky="ew")
        self.yuzu_data_actions_frame.grid_columnconfigure(1, weight=1)

        self.yuzu_import_optionmenu = customtkinter.CTkOptionMenu(self.yuzu_data_actions_frame, width=300, values=["All Data", "Save Data", "Custom..."])
        self.yuzu_export_optionmenu = customtkinter.CTkOptionMenu(self.yuzu_data_actions_frame, width=300, values=["All Data", "Save Data", "Custom..."])
        self.yuzu_delete_optionmenu = customtkinter.CTkOptionMenu(self.yuzu_data_actions_frame, width=300, values=["All Data", "Save Data", "Custom..."])

        self.yuzu_import_button = customtkinter.CTkButton(self.yuzu_data_actions_frame, text="Import", command=self.import_data_button_event)
        self.yuzu_export_button = customtkinter.CTkButton(self.yuzu_data_actions_frame, text="Export", command=self.export_data_button_event)
        self.yuzu_delete_button = customtkinter.CTkButton(self.yuzu_data_actions_frame, text="Delete", command=self.delete_data_button_event, fg_color="red", hover_color="darkred")

        self.yuzu_import_optionmenu.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.yuzu_import_button.grid(row=0, column=1, padx=10, pady=10, sticky="e")
        self.yuzu_export_optionmenu.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.yuzu_export_button.grid(row=1, column=1, padx=10, pady=10, sticky="e")
        self.yuzu_delete_optionmenu.grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.yuzu_delete_button.grid(row=2, column=1, padx=10, pady=10, sticky="e")

        self.yuzu_data_log = customtkinter.CTkFrame(self.manage_data_frame)
        self.yuzu_data_log.grid(row=1, column=0, padx=20, pady=20, columnspan=3, sticky="new")
        self.yuzu_data_log.grid_columnconfigure(0, weight=1)
        self.yuzu_data_log.grid_rowconfigure(1, weight=1)
        self.yuzu.data_progress_frame = ProgressFrame(self.yuzu_data_log)
        # create yuzu downloader button, frame and widgets

        self.early_access_actions_frame.grid_propagate(False)
        self.mainline_actions_frame.grid_propagate(False)
        self.selected_channel.set(self.settings.yuzu.current_yuzu_channel)
        self.switch_channel()

        self.manage_roms_frame = customtkinter.CTkFrame(self, corner_radius=0, bg_color="transparent")
        self.manage_roms_frame.grid_columnconfigure(0, weight=1)
        self.manage_roms_frame.grid_rowconfigure(0, weight=1)
        self.rom_frame = YuzuROMFrame(self.manage_roms_frame, self.settings, self.cache)
        self.rom_frame.grid(row=0, column=0,  padx=20, pady=20, sticky="nsew")

    def manage_roms_button_event(self):
        self.rom_frame.current_roms_frame.check_titles_db()
        self.select_frame_by_name("roms")

    def configure_data_buttons(self, **kwargs):
        self.yuzu_delete_button.configure(**kwargs)
        self.yuzu_import_button.configure(**kwargs)
        self.yuzu_export_button.configure(**kwargs)

    def configure_mainline_buttons(self, state, **kwargs):
        self.launch_mainline_button.configure(state=state, **kwargs)
        self.install_mainline_button.configure(state=state)
        self.delete_mainline_button.configure(state=state)

    def configure_early_access_buttons(self, state, **kwargs):
        self.install_early_access_button.configure(state=state)
        self.launch_early_access_button.configure(state=state, **kwargs)
        self.delete_early_access_button.configure(state=state)

    def switch_channel(self, value=None):
        value = self.selected_channel.get()
        self.settings.yuzu.current_yuzu_channel = value
        self.settings.update_file()
        if value == "Mainline":
            self.image_button.configure(image=self.mainline_image)
            self.mainline_actions_frame.grid(row=2, column=0, columnspan=3)
        else:
            self.mainline_actions_frame.grid_forget()
        if value == "Early Access":
            self.image_button.configure(image=self.early_access_image)
            self.early_access_actions_frame.grid(row=2, column=0, columnspan=3)
        else:
            self.early_access_actions_frame.grid_forget()

    def launch_mainline_button_event(self, event=None):
        if event is None or self.launch_mainline_button.cget("state") == "disabled":
            return
        if self.launch_mainline_button.cget("state") == "disabled":
            return
        if not os.path.exists(os.path.join(self.settings.yuzu.install_directory, "yuzu-windows-msvc", "yuzu.exe")):
            messagebox.showerror("Yuzu", "Installation of yuzu not found, please install yuzu using the button to the left")
            return
        self.configure_mainline_buttons("disabled")
        self.configure_early_access_buttons("disabled")
        self.firmware_keys_frame.configure_firmware_key_buttons("disabled")
        shift_clicked = True if event.state & 1 else False
        shift_clicked = not shift_clicked if self.settings.app.disable_automatic_updates == "True" else shift_clicked
        thread = Thread(target=self.yuzu.launch_yuzu_handler, args=("mainline", shift_clicked, ))
        thread.start()
        Thread(target=self.enable_buttons_after_thread, args=(thread, ["mainline", "early_access", "firmware_keys"],)).start()

    def install_mainline_button_event(self, event=None):
        if event is None or self.install_mainline_button.cget("state") == "disabled":
            return
        if self.settings.yuzu.use_yuzu_installer == "False" and os.path.exists(os.path.join(self.settings.yuzu.install_directory, "yuzu-windows-msvc")) and not messagebox.askyesno("Directory Exists", "The directory already exists. Are you sure you want to overwrite the contents inside?"):
            return
        path_to_archive = None
        if event.state & 1:
            path_to_archive = PathDialog(filetypes=(".zip",), title="Custom Yuzu Archive", text="Enter path to yuzu archive: ")
            path_to_archive = path_to_archive.get_input()
            if not all(path_to_archive):
                if path_to_archive[1] is not None:
                    messagebox.showerror("Error", "The path you have provided is invalid")
                return
            path_to_archive = path_to_archive[1]
        else:
            messagebox.showerror("Error", "Yuzu has been discontinued due to a lawsuit. You may still use a ZIP file to install Yuzu. This can be done by shift-clicking the install button.")
            return
        self.configure_mainline_buttons("disabled")
        self.configure_early_access_buttons("disabled")
        self.firmware_keys_frame.configure_firmware_key_buttons("disabled")
        thread = Thread(target=self.yuzu.launch_yuzu_installer) if self.settings.yuzu.use_yuzu_installer == "True" and path_to_archive is None else Thread(target=self.yuzu.install_release_handler, args=("mainline", False, path_to_archive))
        thread.start()
        Thread(target=self.enable_buttons_after_thread, args=(thread, ["mainline", "early_access", "firmware_keys"],)).start()

    def launch_early_access_button_event(self, event=None):
        if event is None or self.launch_early_access_button.cget("state") == "disabled":
            return
        if self.launch_early_access_button.cget("state") == "disabled":
            return
        if not os.path.exists(os.path.join(self.settings.yuzu.install_directory, "yuzu-windows-msvc-early-access", "yuzu.exe")):
            messagebox.showerror("Yuzu", "Installation of yuzu early access not found, please install yuzu early access using the button to the left")
            return
        self.configure_mainline_buttons("disabled")
        self.configure_early_access_buttons("disabled")
        self.firmware_keys_frame.configure_firmware_key_buttons("disabled")
        shift_clicked = True if event.state & 1 else False
        shift_clicked = not shift_clicked if self.settings.app.disable_automatic_updates == "True" else shift_clicked
        thread = Thread(target=self.yuzu.launch_yuzu_handler, args=("early_access", shift_clicked, ))
        thread.start()
        Thread(target=self.enable_buttons_after_thread, args=(thread, ["mainline", "early_access", "firmware_keys"],)).start()

    def install_early_access_button_event(self, event=None):
        if event is None or self.install_early_access_button.cget("state") == "disabled":
            return
        if self.settings.yuzu.use_yuzu_installer == "False" and os.path.exists(os.path.join(self.settings.yuzu.install_directory, "yuzu-windows-msvc-early-access")) and not messagebox.askyesno("Directory Exists", "The directory already exists, are you sure you want to overwrite the contents inside?"):
            return
        path_to_archive = None
        if event.state & 1:
            path_to_archive = PathDialog(filetypes=(".zip",), title="Custom Yuzu EA Archive", text="Enter path to yuzu early access archive: ")
            path_to_archive = path_to_archive.get_input()
            if not all(path_to_archive):
                if path_to_archive[1] is not None:
                    messagebox.showerror("Error", "The path you have provided is invalid")
                return
            path_to_archive = path_to_archive[1]
        else:
            messagebox.showerror("Error", "Yuzu has been discontinued due to a lawsuit. You may still use a ZIP file to install Yuzu. This can be done by shift-clicking the install button.")
            return
        self.configure_mainline_buttons("disabled")
        self.configure_early_access_buttons("disabled")
        self.firmware_keys_frame.configure_firmware_key_buttons("disabled")

        thread = Thread(target=self.yuzu.launch_yuzu_installer) if self.settings.yuzu.use_yuzu_installer == "True" and path_to_archive is None else Thread(target=self.yuzu.install_release_handler, args=("early_access", False, path_to_archive))
        thread.start()
        Thread(target=self.enable_buttons_after_thread, args=(thread, ["mainline", "early_access", "firmware_keys"],)).start()

    def delete_early_access_button_event(self):
        if not os.path.exists(os.path.join(self.settings.yuzu.install_directory, "yuzu-windows-msvc-early-access")):
            messagebox.showinfo("Delete Yuzu EA", f"Could not find a yuzu EA installation at {os.path.join(self.settings.yuzu.install_directory, 'yuzu-windows-msvc-early-access')} ")
            return
        if not messagebox.askyesno("Delete Yuzu EA", f"Are you sure you want to delete yuzu early access and its contents from {os.path.join(self.settings.yuzu.install_directory, "yuzu-windows-msvc-early-access")}?"):
            return

        self.configure_early_access_buttons("disabled")
        thread = Thread(target=self.yuzu.delete_early_access)
        thread.start()
        Thread(target=self.enable_buttons_after_thread, args=(thread, ["early_access"],)).start()

    def delete_mainline_button_event(self):
        if not os.path.exists(os.path.join(self.settings.yuzu.install_directory, "yuzu-windows-msvc")):
            messagebox.showinfo("Delete Yuzu", f"Could not find a yuzu installation at {os.path.join(self.settings.yuzu.install_directory, 'yuzu-windows-msvc')} ")
            return
        if not messagebox.askyesno("Delete Yuzu", f"Are you sure you want to delete yuzu and its contents from '{os.path.join(self.settings.yuzu.install_directory, "yuzu-windows-mscv")}'?"):
            return
        self.configure_mainline_buttons("disabled")
        thread = Thread(target=self.yuzu.delete_mainline)
        thread.start()
        Thread(target=self.enable_buttons_after_thread, args=(thread, ["mainline"],)).start()

    def install_firmware_button_event(self, event=None):
        if event is None or self.firmware_keys_frame.install_firmware_button.cget("state") == "disabled":
            return
        path_to_archive = None
        if event.state & 1:
            path_to_archive = PathDialog(filetypes=(".zip",), title="Custom Firmware Archive", text="Type path to Firmware Archive: ")
            path_to_archive = path_to_archive.get_input()
            if not all(path_to_archive):
                if path_to_archive[1] is not None:
                    messagebox.showerror("Error", "The path you have provided is invalid")
                return
            path_to_archive = path_to_archive[1]
            args = ("path", path_to_archive, )
        else:
            if self.firmware_keys_frame.firmware_option_menu.cget("state") == "disabled":
                messagebox.showerror("Error", "Please ensure that a correct version has been chosen from the menu to the left")
                return
            release = self.firmware_keys_frame.firmware_key_version_dict["firmware"][self.firmware_keys_frame.firmware_option_menu_variable.get()]
            args = ("release", release)
        self.firmware_keys_frame.configure_firmware_key_buttons("disabled")
        self.configure_mainline_buttons("disabled")
        self.configure_early_access_buttons("disabled")
        thread = Thread(target=self.yuzu.install_firmware_handler, args=args)
        thread.start()
        Thread(target=self.enable_buttons_after_thread, args=(thread, ["firmware_keys", "mainline", "early_access"], )).start()

    def install_keys_button_event(self, event=None):
        if event is None or self.firmware_keys_frame.install_keys_button.cget("state") == "disabled":
            return
        path_to_archive = None
        if event.state & 1:
            path_to_archive = PathDialog(filetypes=(".zip", ".keys"), title="Custom Key Archive", text="Type path to Key Archive: ")
            path_to_archive = path_to_archive.get_input()
            if not all(path_to_archive):
                if path_to_archive[1] is not None:
                    messagebox.showerror("Error", "The path you have provided is invalid")
                return
            path_to_archive = path_to_archive[1]
            args = ("path", path_to_archive, )
        else:
            if self.firmware_keys_frame.key_option_menu.cget("state") == "disabled":
                messagebox.showerror("Error", "Please ensure that a correct version has been chosen from the menu to the left")
                return
            release = self.firmware_keys_frame.firmware_key_version_dict["keys"][self.firmware_keys_frame.key_option_menu_variable.get()]
            args = ("release", release, )
        self.firmware_keys_frame.configure_firmware_key_buttons("disabled")
        self.configure_mainline_buttons("disabled")
        self.configure_early_access_buttons("disabled")

        thread = Thread(target=self.yuzu.install_key_handler, args=args)
        thread.start()
        Thread(target=self.enable_buttons_after_thread, args=(thread, ["firmware_keys", "mainline", "early_access"],)).start()

    def import_data_button_event(self):
        directory = None
        folders = None
        import_option = self.yuzu_import_optionmenu.get()

        if import_option == "Custom...":
            directory, folders = FolderSelector(
                title="Choose directory and folders to import",
                allowed_folders=FOLDERS
            ).get_input()
        else:
            directory = PathDialog(title="Import Directory", text="Enter directory to import from: ", directory=True).get_input()
            if directory and directory[1] is not None:
                directory = directory[1]
            else:
                messagebox.showerror("Error", "The path you have provided is invalid")
                return

        if directory is None:
            return

        self.configure_data_buttons(state="disabled")
        thread_args = (import_option, directory, folders, ) if folders else (import_option, directory, )
        thread = Thread(target=self.yuzu.import_yuzu_data, args=thread_args)
        thread.start()
        Thread(target=self.enable_buttons_after_thread, args=(thread, ["data"],)).start()

    def export_data_button_event(self):
        directory = PathDialog(title="Export Directory", text="Enter directory to export to: ", directory=True)
        directory = directory.get_input()
        if not all(directory):
            if directory[1] is not None:
                messagebox.showerror("Error", "The path you have provided is invalid")
                return
            return
        directory = directory[1]
        if self.yuzu_export_optionmenu.get() == "Custom...":
            user_directory, folders = FolderSelector(title="Choose folders to export", predefined_directory=self.settings.yuzu.user_directory, allowed_folders=FOLDERS).get_input()
            if user_directory is None or folders is None:
                return
            args = ("Custom...", directory, folders,)
        else:
            args = (self.yuzu_export_optionmenu.get(), directory,)

        self.configure_data_buttons(state="disabled")
        thread = Thread(target=self.yuzu.export_yuzu_data, args=args)
        thread.start()
        Thread(target=self.enable_buttons_after_thread, args=(thread, ["data"],)).start()

    def delete_data_button_event(self):
        if self.yuzu_delete_optionmenu.get() == "Custom...":
            directory, folders = FolderSelector(title="Delete Directory", predefined_directory=self.settings.yuzu.user_directory, allowed_folders=FOLDERS).get_input()
            if directory is None or folders is None:
                return
            thread = Thread(target=self.yuzu.delete_yuzu_data, args=("Custom...", folders,))
        else:
            thread = Thread(target=self.yuzu.delete_yuzu_data, args=(self.yuzu_delete_optionmenu.get(),))
        if not messagebox.askyesno("Confirmation", "This will delete the data from Yuzu's directory. This action cannot be undone, are you sure you wish to continue?"):
            return
        self.configure_data_buttons(state="disabled")
        thread.start()
        Thread(target=self.enable_buttons_after_thread, args=(thread, ["data"],)).start()

    def enable_buttons_after_thread(self, thread, buttons):
        thread.join()
        for button in buttons:
            if button == "mainline":
                self.configure_mainline_buttons("normal", text="Launch Yuzu  ", width=200)
            elif button == "early_access":
                self.configure_early_access_buttons("normal", text="Launch Yuzu EA  ", width=200)
            elif button == "firmware_keys":
                self.firmware_keys_frame.configure_firmware_key_buttons("normal")
            elif button == "data":
                self.configure_data_buttons(state="normal")
        self.fetch_versions()

    def fetch_versions(self, installed_only=True):
        self.installed_mainline_version = self.metadata.get_installed_version("mainline")
        self.installed_early_access_version = self.metadata.get_installed_version("early_access")
        self.installed_firmware_version = self.metadata.get_installed_version("yuzu_firmware")
        self.installed_key_version = self.metadata.get_installed_version("yuzu_keys")
        self.update_version_text()

    def update_version_text(self):
        if self.early_access_version is not None and self.install_early_access_button.cget("state") != "disabled":
            self.install_early_access_button.configure(text=f"Install Yuzu EA {self.early_access_version}")
        if self.mainline_version is not None and self.install_mainline_button.cget("state") != "disabled":
            self.install_mainline_button.configure(text=f"Install Yuzu {self.mainline_version}")
        if self.installed_mainline_version != "":
            if self.launch_mainline_button.cget("state") != "disabled":
                self.launch_mainline_button.configure(text=f"Launch Yuzu {self.installed_mainline_version}  ")
        else:
            self.launch_mainline_button.configure(text="Launch Yuzu  ")
        if self.installed_early_access_version != "":
            if self.launch_early_access_button.cget("state") != "disabled":
                self.launch_early_access_button.configure(text=F"Launch Yuzu EA {self.installed_early_access_version}  ")
        else:
            self.launch_early_access_button.configure(text="Launch Yuzu EA  ")

        self.firmware_keys_frame.installed_firmware_version_label.configure(text=self.installed_firmware_version.replace("Rebootless Update", "RU") if self.installed_firmware_version != "" else "Not Installed")
        self.firmware_keys_frame.installed_key_version_label.configure(text=self.installed_key_version if self.installed_key_version != "" else "Not Installed")
