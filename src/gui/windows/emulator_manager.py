import os
import shutil
import webbrowser
from sys import exit as sysexit
from threading import Thread
from tkinter import messagebox
from packaging import version

import customtkinter
from customtkinter import ThemeManager
from PIL import Image

from gui.frames.dolphin.dolphin_frame import DolphinFrame
from gui.frames.ryujinx.ryujinx_frame import RyujinxFrame
from gui.frames.settings.settings_frame import SettingsFrame
from gui.frames.yuzu.yuzu_frame import YuzuFrame
from gui.frames.xenia.xenia_frame import XeniaFrame
from gui.windows.progress_window import ProgressWindow
from settings.app_settings import load_customtkinter_themes
from settings.cache import Cache
from settings.metadata import Metadata
from settings.settings import Settings
from utils.auth_token_manager import delete_token_file
from utils.logger import setup_logger
from utils.requests_utils import (fetch_firmware_keys_dict, get_all_releases,
                                  get_headers)


class EmulatorManager(customtkinter.CTk):
    def __init__(self, root_dir, open_app_settings=False, pos=None):
        self.just_opened = True
        super().__init__()
        self.logger = setup_logger(__name__)
        self.logger.info("Initialising Emulator Manager")
        self.logger.info("Initialising Settings...")
        self.settings = Settings(self, root_dir)
        self.logger.info("Initialising Metadata...")
        self.metadata = Metadata(self, self.settings)
        self.logger.info("Initialising Cache...")
        self.cache = Cache(self, self.settings, self.metadata)
        self.version = "v0.13.8"
        self.root_dir = root_dir
        if pos is None:
            pos = ["", ""]
        self.x = pos[0]
        self.y = pos[1]
        try:
            self.logger.info("Defining images")
            self.define_images()
        except FileNotFoundError:
            self.logger.critical("Missing image files. Exiting...")
            messagebox.showerror("Image Error", "The image files could not be found, try re-downloading the latest release from the GitHub repository.", master=self)
            return
        self.build_gui()
        self.just_opened = False
        if open_app_settings:
            self.select_frame_by_name("settings")
            self.settings_frame.select_settings_frame_by_name("app")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.yuzu_frame.fetch_versions()
        self.ryujinx_frame.fetch_versions()
        self.dolphin_frame.fetch_versions()
        self.xenia_frame.fetch_versions()
        if not open_app_settings and self.settings.app.check_for_app_updates == "True":
            Thread(target=self.check_for_update).start()

    def define_images(self):
        self.dolphin_logo = customtkinter.CTkImage(Image.open(self.settings.get_image_path("dolphin_logo")), size=(26, 26))
        self.dolphin_banner = customtkinter.CTkImage(light_image=Image.open(self.settings.get_image_path("dolphin_banner_light")),
                                                     dark_image=Image.open(self.settings.get_image_path("dolphin_banner_dark")), size=(276, 129))
        self.yuzu_logo = customtkinter.CTkImage(Image.open(self.settings.get_image_path("yuzu_logo")), size=(26, 26))
        self.yuzu_mainline = customtkinter.CTkImage(Image.open(self.settings.get_image_path("yuzu_mainline")), size=(120, 40))
        self.yuzu_early_access = customtkinter.CTkImage(Image.open(self.settings.get_image_path("yuzu_early_access")), size=(120, 40))
        self.ryujinx_logo = customtkinter.CTkImage(Image.open(self.settings.get_image_path("ryujinx_logo")), size=(26, 26))
        self.xenia_logo = customtkinter.CTkImage(Image.open(self.settings.get_image_path("xenia_logo")), size=(26, 26))
        self.play_image = customtkinter.CTkImage(light_image=Image.open(self.settings.get_image_path("play_light")),
                                                 dark_image=Image.open(self.settings.get_image_path("play_dark")), size=(20, 20))
        self.settings_image = customtkinter.CTkImage(light_image=Image.open(self.settings.get_image_path("settings_light")),
                                                     dark_image=Image.open(self.settings.get_image_path("settings_dark")), size=(20, 20))
        self.lock_image = customtkinter.CTkImage(light_image=Image.open(self.settings.get_image_path("padlock_light")),
                                                 dark_image=Image.open(self.settings.get_image_path("padlock_dark")), size=(20, 20))
        self.discord_icon = customtkinter.CTkImage(Image.open(self.settings.get_image_path("discord_icon")), size=(22, 22))

    def build_gui(self):
        self.logger.info("Building GUI")
        self.resizable(True, True)  # disable resizing of window
        self.title("Emulator Manager")  # set title of window

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.minsize(1100, 570)  # set the minimum size of the window
        self.geometry("1100x500+{}+{}".format(self.x, self.y))

        # Create navigation frame
        self.navigation_frame = customtkinter.CTkFrame(self, corner_radius=0)
        self.navigation_frame.grid(row=0, column=0, sticky="nsew")
        self.navigation_frame.grid_rowconfigure(1, weight=1)

        # Create navigation frame title.
        self.navigation_frame_label = customtkinter.CTkLabel(self.navigation_frame, text=f"Emulator Manager {self.version.replace("alpha", "a")}",
                                                             compound="left", padx=5, font=customtkinter.CTkFont(size=12, weight="bold"))
        self.navigation_frame_label.grid(row=0, column=0, padx=20, pady=20)
        self.navigation_frame_label.bind('<Double-Button-1>', command=lambda event: messagebox.showinfo("About", f"Emulator Manager {self.version}, made by Viren070 on GitHub."))

        # Create scrollable frame in the middle
        scrollable_frame = customtkinter.CTkScrollableFrame(self.navigation_frame, fg_color="transparent")
        scrollable_frame.grid(row=1, column=0, sticky="nsew")
        self.navigation_frame.grid_rowconfigure(1, weight=1)

        # Create navigation menu buttons
        text_color = ThemeManager.theme["CTkLabel"]["text_color"]
        self.dolphin_button = customtkinter.CTkButton(scrollable_frame, corner_radius=0, height=40, width=100, image=self.dolphin_logo, border_spacing=10, text="Dolphin",
                                                      fg_color="transparent", text_color=text_color,
                                                      anchor="w", command=self.dolphin_button_event)
        self.dolphin_button.grid(row=0, column=0, sticky="ew")

        self.yuzu_button = customtkinter.CTkButton(scrollable_frame, corner_radius=0, height=40, image=self.yuzu_logo, border_spacing=10, text="Yuzu",
                                                   fg_color="transparent", text_color=text_color,
                                                   anchor="w", command=self.yuzu_button_event)
        self.yuzu_button.grid(row=1, column=0, sticky="ew")

        self.ryujinx_button = customtkinter.CTkButton(scrollable_frame, corner_radius=0, height=40, image=self.ryujinx_logo, border_spacing=10, text="Ryujinx",
                                                      fg_color="transparent", text_color=text_color,
                                                      anchor="w", command=self.ryujinx_button_event)
        self.ryujinx_button.grid(row=2, column=0, sticky="ew")
        
        self.xenia_button = customtkinter.CTkButton(scrollable_frame, corner_radius=0, height=40, image=self.xenia_logo, border_spacing=10, text="Xenia",
                                                    fg_color="transparent", text_color=text_color,
                                                    anchor="w", command=lambda: self.select_frame_by_name("xenia"))
        self.xenia_button.grid(row=3, column=0, sticky="ew")
        # Set column weights of scrollable_frame to make buttons expand
        scrollable_frame.grid_columnconfigure(0, weight=1)

        discord_button = customtkinter.CTkButton(self.navigation_frame, height=25, width=100, corner_radius=20, text="Join Discord", image=self.discord_icon, border_spacing=10, command=self.show_discord_invite)
        discord_button.grid(row=2, column=0, pady=10)
        # Create settings button at the bottom
        self.settings_button = customtkinter.CTkButton(self.navigation_frame, corner_radius=0, height=40, image=self.settings_image, border_spacing=10, text="Settings",
                                                       fg_color="transparent", text_color=text_color,
                                                       anchor="w", command=self.settings_button_event)
        self.settings_button.grid(row=3, column=0, sticky="ew")
        self.logger.info("Initialising frames...")
        self.yuzu_frame = YuzuFrame(self, self.settings, self.metadata, self.cache)
        self.logger.info("Initialised Yuzu Frame")
        self.dolphin_frame = DolphinFrame(self, self.settings, self.metadata, self.cache)
        self.logger.info("Initialised Dolphin Frame")
        self.ryujinx_frame = RyujinxFrame(self, self.settings, self.metadata, self.cache)
        self.logger.info("Initialised Ryujinx Frame")
        self.xenia_frame = XeniaFrame(self, self.settings, self.metadata, self.cache)
        self.logger.info("Initialised Xenia Frame")
        self.settings_frame = SettingsFrame(self, self.settings)
        self.logger.info("Initialised Settings Frame")

    def show_discord_invite(self):
        if messagebox.askyesno("Discord Invite", "Would you like to join the Emulator Manager Discord server?\n\nBy joining, you can get help with any issues you may have, as well as get notified of any updates or new features.\n\nIf you click yes, your default web browser will open the invite link."):
            webbrowser.open("https://discord.gg/9Dn9mSxW6t")
    def dolphin_button_event(self):
        self.select_frame_by_name("dolphin")

    def yuzu_button_event(self):

        self.select_frame_by_name("yuzu")

    def ryujinx_button_event(self):
        self.select_frame_by_name("ryujinx")

    def settings_button_event(self):
        self.select_frame_by_name("settings")

    def select_frame_by_name(self, name):
        if not self.just_opened and (self.settings_changed()) and name != "settings":
            if messagebox.askyesno("Confirmation", "You have unsaved changes in the settings. If you leave now, the changes you made will be discarded. Continue?"):
                self.revert_settings()
            else:
                return
        self.settings_button.configure(fg_color=self.settings_button.cget("hover_color") if name == "settings" else "transparent")
        self.dolphin_button.configure(fg_color=self.dolphin_button.cget("hover_color") if name == "dolphin" else "transparent")
        self.yuzu_button.configure(fg_color=self.yuzu_button.cget("hover_color") if name == "yuzu" else "transparent")
        self.ryujinx_button.configure(fg_color=self.ryujinx_button.cget("hover_color") if name == "ryujinx" else "transparent")
        self.xenia_button.configure(fg_color=self.xenia_button.cget("hover_color") if name == "xenia" else "transparent")

        # show selected frame
        if name == "settings":
            self.settings_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.settings_frame.grid_forget()
            self.settings_frame.select_settings_frame_by_name(None)

        if name == "dolphin":
            self.dolphin_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.dolphin_frame.grid_forget()
            self.dolphin_frame.select_frame_by_name(None)
        if name == "yuzu":
            self.yuzu_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.yuzu_frame.grid_forget()
            self.yuzu_frame.select_frame_by_name(None)
        if name == "ryujinx":
            self.ryujinx_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.ryujinx_frame.grid_forget()
            self.ryujinx_frame.select_frame_by_name(None)
        if name == "xenia":
            self.xenia_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.xenia_frame.grid_forget()
            self.xenia_frame.select_frame_by_name(None)

    def settings_changed(self):
        return self.settings_frame.settings_changed()

    def revert_settings(self):
        self.settings_frame.revert_settings()

    def restart(self):
        # for after_id in self.tk.eval('after info').split():
        #     self.after_cancel(after_id)
        pos = [self.winfo_x(), self.winfo_y()]
        self.destroy()
        load_customtkinter_themes(os.path.join(self.root_dir, "assets", "themes"))
        EmulatorManager(self.root_dir, True, pos)

    def check_for_update(self):
        releases = get_all_releases("https://api.github.com/repos/Viren070/Emulator-Manager/releases?per_page=10", headers=get_headers(self.settings.app.token))
        if not all(releases):
            return
        releases = releases[1]
        releases.sort(key=lambda r: version.parse(r["tag_name"]), reverse=True)

        latest_release = releases[0]

        if version.parse(latest_release["tag_name"]) > version.parse(self.version):
            is_alpha = "alpha" in latest_release["tag_name"]
            self.prompt_update(latest_release["tag_name"], is_alpha)

    def prompt_update(self, version, is_alpha):
        release_type = "alpha" if is_alpha else "stable"
        alpha_warning = "\nPlease note that alpha releases are unstable and bugs are to be expected." if is_alpha else ""
        if messagebox.askyesno("Update Available", f"There is a new {release_type} update ({version}) available to download from the GitHub Repository.{alpha_warning} \nWould you like to download it now?"):
            webbrowser.open(f"https://github.com/Viren070/Emulator-Manager/releases/tag/{version}")

    def on_closing(self):
        if (self.dolphin_frame.dolphin.running or self.yuzu_frame.yuzu.running):
            messagebox.showerror("Emulator Manager", "Please close any emulators before attempting to exit.")
            return
        temp_folder = os.path.join(os.getenv("TEMP"), "Emulator Manager")
        if os.path.exists(temp_folder):
            try:
                shutil.rmtree(temp_folder)
            except PermissionError:
                pass
        delete_token_file()
        sysexit()
