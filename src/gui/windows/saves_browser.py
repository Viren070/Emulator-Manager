import os
import textwrap
from tkinter import messagebox
from urllib.parse import unquote
from threading import Thread

import customtkinter

from gui.windows.progress_window import ProgressWindow
from utils.downloader import download_through_stream
from utils.requests_utils import create_get_connection, get_headers
from utils.logger import setup_logger


class SavesBrowser(customtkinter.CTkToplevel):
    def __init__(self, title, saves, title_id, *args, **kwargs):
        self.logger = setup_logger(__name__)
        self.logger.info(f"Initalising SavesBrowser for {title}: {title_id} with {len(saves)} save(s).")
        super().__init__(*args, **kwargs)
        self.title(title)
        self.saves = saves
        self.lift()  # lift window on top
        self.attributes("-topmost", True)  # stay on top
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.after(30, self.build_frame)  # create widgets with slight delay, to avoid white flickering of background
        self.grab_set()  # make other windows not clickable

    def build_frame(self):
        self.resizable(False, True)
        self.minsize(415, 400)
        self.geometry("415x600")
        # Create a label for the title
        title_label = customtkinter.CTkLabel(self, text="Download Saves", font=customtkinter.CTkFont("Arial", 20), anchor="center")
        title_label.grid(row=0, column=0, sticky="nsew")

        # Create a label for the paragraph
        paragraph_label = customtkinter.CTkLabel(self, font=customtkinter.CTkFont("Arial", 15), anchor="center", text=textwrap.fill("Once the download is complete, the save file will be placed on your desktop. To install a save, right click then game in the emulator game list, "'open save folder'" and extract the downloaded archive there. Be sure to backup your current save file if you want to use it later!", 60))
        paragraph_label.grid(row=1, column=0, pady=20, sticky="nsew")

        # Create a vertically scrollable frame
        scrollable_frame = customtkinter.CTkScrollableFrame(self)
        scrollable_frame.grid(row=2, column=0, sticky="nsew")

        for i, save in enumerate(self.saves):
            filename = unquote(save).split('/')[-1].split(".zip")[-2]

            # Create a button for the save
            save_button_text = textwrap.fill(filename, width=42)  # Insert newlines into the filename
            save_button = customtkinter.CTkButton(scrollable_frame, text=save_button_text, font=customtkinter.CTkFont("Arial", 20), anchor="w", command=lambda save=save: Thread(target=self.download_save, args=(save, )).start())
            save_button.grid(row=i, column=0, padx=(2,10), pady=5, sticky="ew")
            
        # Configure the grid to allocate all extra space to the scrollable frame
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
    def download_save(self, save):
        self.logger.info(f"Downloading save: {save}")
        progress_window = ProgressWindow(title="Downloading Save")
        self.attributes("-topmost", False)
        self.grab_release()
        progress_window.lift()
        progress_window.attributes("-topmost", True)
        progress_window.grab_set()
        progress_frame = progress_window.progress_frame
        progress_frame.start_download("Save File", 0)
        progress_frame.update_status_label("Fetching save file...")
        base_url = "https://raw.githubusercontent.com/Viren070/NX_Saves/main/nintendo/switch/savegames/"
        save_download_url = base_url + save
        response_result = create_get_connection(save_download_url, headers=get_headers(), stream=True)
        if not all(response_result):
            messagebox.showerror("Download Error", "An error occurred while downloading the save file.")
            progress_window.destroy()
            return 
        response = response_result[1]
        filename = unquote(save).split('/')[-1].split(".zip")[-2]
        download_path = os.path.join(os.path.expanduser("~"), "Desktop", f"{filename}.zip")
        progress_frame.start_download(filename, int(response.headers.get("content-length", 0)))
        download_result = download_through_stream(response, download_path, progress_frame, chunk_size=1024*128)
        progress_frame.complete_download()
        progress_window.grab_release()
        progress_window.destroy()
        if not all(download_result):
            messagebox.showerror("Download Error", "An error occurred while downloading the save file.")
            return 
        messagebox.showinfo("Download Complete", "The save file has been downloaded to your desktop.")
        self.lift()
        self.attributes("-topmost", True)
        self.grab_set()
        
    def on_closing(self):
        self.grab_release()
        self.destroy()  # destroy window