import webbrowser

import customtkinter

from core.logging.logger import Logger
from core.network.myrient import get_game_download_url, get_list_of_games
from gui.frames.game_list_frame import GameListFrame
from gui.libs.CTkMessagebox import messagebox


class MyrientGameListFrame(GameListFrame):
    def __init__(self, master, event_manager, cache, myrient_path, console_name, download_button_event):
        self.myrient_path = myrient_path
        self.console_name = console_name
        self.cache = cache
        self.download_button_event = download_button_event
        super().__init__(master=master, event_manager=event_manager)
        self.logger = Logger(__name__).get_logger()

    def get_game_list(self):
        cache_lookup_result = self.cache.get_json(f"{self.console_name}_games")
        if cache_lookup_result["status"]:
            self.logger.info("game list cache hit")
            game_list = cache_lookup_result["data"]
            return {
                "result": (game_list, ),
                "message": {
                    "function": messagebox.showsuccess,
                    "arguments": (self.winfo_toplevel(), "Success", "Successfully retrieved games from cache.")
                }
            }
        self.logger.info("game list cache miss")
        scrape_result = get_list_of_games(myrient_path=self.myrient_path)
        if not scrape_result["status"]:
            return {
                "result": ([], ),
                "message": {
                    "function": messagebox.showerror,
                    "arguments": (self.winfo_toplevel(), "Error", "Failed to fetch games.")
                }
            }
        self.cache.add_json(f"{self.console_name}_games", scrape_result["games"])
        return {
            "result": (scrape_result["games"],),
            "message": {
                "function": messagebox.showsuccess,
                "arguments": (self.winfo_toplevel(), "Success", "Successfully fetched games.")
            }
        }

    def add_game_to_frame(self, game, row_counter):
        game_download_url = get_game_download_url(game_name=game, myrient_path=self.myrient_path)
        entry = customtkinter.CTkEntry(self.result_frame, width=400)
        entry.insert(0, game)
        entry.configure(state="disabled")

        entry.grid(row=row_counter, column=0, padx=10, pady=5, sticky="w")
        button = customtkinter.CTkButton(self.result_frame, text="Download")
        button.configure(command=lambda button=button, game=game: self.download_button_event(game, self.myrient_path))
        button.bind("<Shift-Button-1>", lambda event, game=game: webbrowser.open(game_download_url))
        button.grid(row=row_counter, column=1, padx=10, pady=5, sticky="e")
