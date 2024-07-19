import json
import os
import base64
import shutil
import textwrap
import time
from threading import Thread
from tkinter import filedialog, messagebox

import customtkinter
from PIL import Image
from webbrowser import open_new_tab

from gui.windows.progress_window import ProgressWindow
from gui.windows.saves_browser import SavesBrowser
from utils.downloader import download_file
from utils.requests_utils import create_get_connection, get_headers
from utils.downloader import download_through_stream


class SwitchTitle:
    def __init__(self, master, title_id, settings, cache):
        print(f"{title_id}: Starting index...")
        self.title_id = title_id
        self.downloading_cover = False
        self.master = master
        self.titles_db = master.titles_db
        self.button = None
        self.frame = None  # The frame that contains the title
        self.settings = settings
        self.cache = cache
        cache_image_lookup_result = self.cache.get_data_from_cache(f"{self.title_id}_icon_search")

        self.title_data = self.gather_metadata()
        
        if not cache_image_lookup_result:
            # if image was not found in cache, set placeholder image and start download in a new thread
            image = settings.get_image_path("placeholder_icon")
            print(f"{title_id}: Starting cover download...")
            Thread(target=self.download_cover, args=(True,)).start()
        else:
            # if image was found in cache, set the image
            print(f"{title_id}: Found cover in cache...")
            image = cache_image_lookup_result["data"]
        self.cover = customtkinter.CTkImage(Image.open(image), size=(224, 224))

    def gather_metadata(self):
        if self.titles_db is None:
            return None
        title_data = self.titles_db.get(self.title_id)
        if title_data is None:
            return None
        return title_data
    
    def get_attribute(self, attribute):
        if self.title_data is None:
            return None
        return self.title_data.get(attribute)

    def download_cover(self, skip_prompt=True):
        if self.downloading_cover:  # if currently downloading cover, return
            return

        # initial checks and prompts
        if self.title_data is None or self.title_data.get("iconUrl") is None:
            if not skip_prompt:
                messagebox.showerror("Download Error", "This game does not have a cover image available.")
            return
        if self.cache.get_data_from_cache(f"{self.title_id}_icon"):
            if not skip_prompt:
                user_confirmation = messagebox.askyesno("Download Cover", "A cover image already exists for this game. Are you sure you want to download a new one?")
                if not user_confirmation:
                    return
                self.cache.remove_from_index(f"{self.title_id}_icon")
            else:
                return
        self.downloading_cover = True
        # create connection to download cover image
        response_result = create_get_connection(self.title_data["iconUrl"], stream=True, headers=get_headers(self.settings.app.token), timeout=30)
        if not all(response_result):
            if not skip_prompt:
                messagebox.showerror("Download Error", f"There was an error while attempting to download the cover image:\n\n {response_result[1]}")
            self.downloading_cover = False
            return
        response = response_result[1]
        # attempt to download cover image
        download_path = os.path.join(os.getcwd(), f"{self.title_id}_icon_search.png")
        download_result = download_file(response, download_path)
        if not all(download_result):
            if not skip_prompt:
                messagebox.showerror("Download Error", f"There was an error while attempting to download the cover image:\n\n {download_result[1]}")
            if os.path.exists(download_path):
                os.remove(download_path)
            self.downloading_cover = False
            return

        # attempt to move downloaded cover image to cache
        move_to_cache_result = self.cache.add_custom_file_to_cache(f"{self.title_id}_icon_search", download_path)
        if not all(move_to_cache_result):
            if not skip_prompt:
                messagebox.showerror("Download Error", f"There was an error while attempting to add the downloaded cover image to cache:\n\n {move_to_cache_result[1]}")
            if os.path.exists(download_path):
                os.remove(download_path)
            self.downloading_cover = False
            return
        # attempt to retrieve the downloaded cover image from cache
        cache_lookup_result = self.cache.get_data_from_cache(f"{self.title_id}_icon_search")
        if not cache_lookup_result:
            if not skip_prompt:
                messagebox.showerror("Download Error", "The cover image could not be retrieved from the cache.")
            if os.path.exists(download_path):
                os.remove(download_path)
            self.downloading_cover = False
            return
        cover_path = cache_lookup_result["data"]
        
        # set the downloaded image as the cover attrbibute
        self.cover = customtkinter.CTkImage(Image.open(cover_path), size=(224, 224))
        
        # update the cover image on the button if it exists
        if self.button is not None:
            self.button.configure(image=self.cover)

        self.downloading_cover = False

class SwitchGamesBrowser(customtkinter.CTkFrame):
    def __init__(self, master, settings, cache):
        super().__init__(master, height=700)
        self.results_per_page = 10
        self.refreshing = False
        self.char_width = customtkinter.CTkFont("Arial", 16).measure("a")
        self.settings = settings
        self.cache = cache
        self.current_page = None
        self.update_in_progress = False
        self.searching = False
        self.build_frame()
        self.define_titles_db()
        self.attempted_update = False
        self.searched_titles = []
        self.current_title_ids = []
        self.total_pages = 0
        self.total_pages_label.configure(text=f"/ {self.total_pages}")
        self.update_results()

    def define_titles_db(self):
        titledb_lookup_result = self.cache.get_data_from_cache("titleDB")  # Check if titles.US.en is cached
        self.titles_db = None
        if titledb_lookup_result is not None and os.path.exists(titledb_lookup_result["data"]):
            with open(titledb_lookup_result["data"], "r", encoding="utf-8") as f:
                self.titles_db = json.load(f)
            Thread(target=self.preprocess_database).start()
    
    def get_current_page_titles(self):
        start_index = (int(self.current_page_entry.get()) - 1) * self.results_per_page
        end_index = start_index + self.results_per_page
        return self.searched_titles[start_index:end_index]


    def build_frame(self):
        # Create a search bar
        search_frame = customtkinter.CTkFrame(self, corner_radius=50)
        search_frame.grid(row=0, column=0, pady=(10, 0), padx=10, sticky="ne")

        self.search_entry = customtkinter.CTkEntry(search_frame, placeholder_text="Search")
        self.search_entry.grid(row=0, column=0, padx=10, pady=10, sticky="e")
        self.search_entry.bind("<Return>", command=lambda event: Thread(target=self.perform_search).start())
        self.search_button = customtkinter.CTkButton(search_frame, text="Go", width=60, command=lambda: Thread(target=self.perform_search).start())
        self.search_button.grid(row=0, column=1, padx=10, sticky="e", pady=10)

        self.result_frame = customtkinter.CTkScrollableFrame(self)
        self.result_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        self.result_frame.grid_columnconfigure(0, weight=1)

        self.current_page = 1

        page_navigation_frame = customtkinter.CTkFrame(self)
        page_navigation_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        left_frame = customtkinter.CTkFrame(page_navigation_frame)
        left_frame.grid(row=0, column=0, padx=(10, 0), pady=10, sticky="w")

        self.current_page_entry = customtkinter.CTkEntry(left_frame, width=35)
        self.current_page_entry.grid(row=0, column=0, padx=(10, 0), pady=10, sticky="nsew")
        self.current_page_entry.insert(0, str(self.current_page))  # Set initial value
        self.current_page_entry.bind("<Return>", self.go_to_page)

        self.total_pages_label = customtkinter.CTkLabel(left_frame, text="/ ")
        self.total_pages_label.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        right_frame = customtkinter.CTkFrame(page_navigation_frame)
        right_frame.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="e")

        button_width = 50

        self.prev_button = customtkinter.CTkButton(right_frame, width=button_width, text=" < ", command=self.go_to_previous_page)
        self.prev_button.grid(row=0, column=0, padx=20, pady=10, sticky="nsew")

        self.next_button = customtkinter.CTkButton(right_frame, width=button_width, text=" > ", command=self.go_to_next_page)
        self.next_button.grid(row=0, column=1, padx=20, pady=10, sticky="nsew")

        page_navigation_frame.grid_columnconfigure(0, weight=1)
        left_frame.grid_columnconfigure(0, weight=1)
        left_frame.grid_columnconfigure(1, weight=0)  # Adjust weight for label
        right_frame.grid_columnconfigure(0, weight=0)  # Adjust weight for buttons
        right_frame.grid_columnconfigure(1, weight=0)

        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=10)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=10)

    def go_to_previous_page(self):
        if self.current_page - 1 == 0:
            self.current_page_entry.delete(0, customtkinter.END)
            self.current_page_entry.insert(0, str(self.current_page))
            return
        self.prev_button.configure(state="disabled")
        self.next_button.configure(state="disabled")
        self.go_to_page(None, self.current_page - 1)

    def go_to_next_page(self):
        if self.current_page + 1 > self.total_pages:
            self.current_page_entry.delete(0, customtkinter.END)
            self.current_page_entry.insert(0, str(self.current_page))
            return
        self.next_button.configure(state="disabled")
        self.prev_button.configure(state="disabled")
        self.go_to_page(None, self.current_page + 1)

    def update_results(self):
        if self.update_in_progress:
            self.next_button.configure(state="normal")
            self.prev_button.configure(state="normal")
            self.search_button.configure(state="normal")
            return
        self.update_in_progress = True
        start_index = (self.current_page - 1) * self.results_per_page
        end_index = (start_index + self.results_per_page) - 1
        for widget in self.result_frame.winfo_children():
            widget.grid_forget()
        row_counter = 0
        if not self.searched_titles:

            prompt_search_label = customtkinter.CTkLabel(self.result_frame, text=textwrap.fill("Use the search bar to search for a game you want to download", 60), font=customtkinter.CTkFont("Arial", 16), anchor="center")
            prompt_search_label.grid(row=0, column=0, sticky="nsew")
            
        for i, game in enumerate(self.searched_titles):
            if i > end_index:
                break
            if i < start_index:
                continue
            # attempt to get necessary metadata for the game
            name = game.get_attribute("name") or "Unknown"
            description = game.get_attribute("description") or "No description available"

            self.current_title_ids.append(game.title_id)
            game_frame = customtkinter.CTkFrame(self.result_frame)
            game_frame.grid(row=row_counter, column=0, padx=10, pady=5, sticky="nsew")
            game_frame.grid_columnconfigure(1, weight=1)  # Allow the second column to expand

            # Game cover button
            game_cover = customtkinter.CTkButton(game_frame, hover_color=None, border_width=0, text="", image=game.cover)
            game.frame = game_frame
            game.button = game_cover
            game_cover.bind("<Shift-Button-3>", command=lambda event, game=game: Thread(target=game.download_cover, args=(False, )).start())
            game_cover.grid(row=0, column=0, rowspan=3, padx=10, pady=5, sticky="nsew")  # Span 3 rows
            
            # Game name label
            game_name_label = customtkinter.CTkLabel(game_frame, text=name, font=customtkinter.CTkFont("Arial", 16))
            game_name_label.grid(row=0, column=1, padx=10, columnspan=2, pady=5, sticky="nsew")

            # Game description text box
            game_desc_text = customtkinter.CTkTextbox(game_frame, height=130, border_width=0, fg_color="transparent")
            game_desc_text.insert(customtkinter.END, description)
            game_desc_text.configure(state="disabled")  # Make the text box read-only
            game_desc_text.grid(row=1, column=1, padx=10, columnspan=2, pady=5, sticky="nsew")

            # Game download button
            game_download_button = customtkinter.CTkButton(game_frame, text="Download", width=20, corner_radius=50, command=lambda game=game: self.download_game(game))
            game_download_button.grid(row=2, column=1, padx=10, pady=5, sticky="nsew")
            
            row_counter += 1

        self.current_page_entry.delete(0, customtkinter.END)
        self.current_page_entry.insert(0, str(self.current_page))
        self.next_button.configure(state="normal")
        self.prev_button.configure(state="normal")
        self.search_button.configure(state="normal")
        self.update_in_progress = False

    def preprocess_database(self):
        print("Preprocessing database...")
        self.inverted_index = {}
        for game_id, game_info in self.titles_db.items():
            if self.is_update(game_id) or self.is_dlc(game_id):
                continue
            # Process 'name' and 'description' fields
            for field in ['name']:
                text = game_info.get(field, "")
                if text is None:
                    continue
                text = text.lower()  # Ensure lowercase for consistency
                tokens = set(text.split())  # Simple tokenization by splitting on whitespace
                for token in tokens:
                    if token not in self.inverted_index:
                        self.inverted_index[token] = set()
                    self.inverted_index[token].add(game_id)
            
            # Process 'category' field separately since it's a list
            categories = game_info.get('category', [])
            if categories is None:
                continue
            for category in categories:
                category = category.lower()  # Ensure lowercase for consistency
                if category not in self.inverted_index:
                    self.inverted_index[category] = set()
                self.inverted_index[category].add(game_id)
        print("Preprocessing complete.")
                    
    def perform_search(self, *args):
        if self.searching:
            return

        query = self.search_entry.get().lower()
        if not query or len(query) < 3:
            return 
        if not self.titles_db:
            self.searched_titles = []
            self.define_titles_db()
            return
        self.search_button.configure(state="disabled")
        self.searching = True
        query_tokens = query.split()
        matching_game_ids = set()
        for token in query_tokens:
            if token in self.inverted_index:
                if not matching_game_ids:
                    matching_game_ids = self.inverted_index[token]
                else:
                    matching_game_ids.intersection_update(self.inverted_index[token])
        
        # cut of after 50 results 
        matching_game_ids = list(matching_game_ids)[:50]
        # Retrieve the full game details for the matching IDs
        self.searched_titles = [SwitchTitle(self, game_id, self.settings, self.cache) for game_id in matching_game_ids]
        self.total_pages = (len(self.searched_titles) + self.results_per_page - 1) // self.results_per_page
        self.total_pages_label.configure(text=f"/ {self.total_pages}")
        self.current_page = 1
        self.update_results()
        self.searching = False

    def go_to_page(self, event=None, page_no=None):
        if self.update_in_progress:
            self.current_page_entry.delete(0, customtkinter.END)
            self.current_page_entry.insert(0, str(self.current_page))
            self.next_button.configure(state="normal")
            self.prev_button.configure(state="normal")
            return

        try:
            page_number = int(self.current_page_entry.get()) if page_no is None else int(page_no)
            if page_number == self.current_page:
                return
            if 1 <= page_number <= self.total_pages:
                self.current_page = page_number
                self.current_page_entry.delete(0, customtkinter.END)
                self.current_page_entry.insert(0, str(self.current_page))
                Thread(target=self.update_results).start()
            else:
                # Display an error message or handle invalid page numbers
                self.current_page_entry.delete(0, customtkinter.END)
                self.current_page_entry.insert(0, str(self.current_page))
        except ValueError:
            # Handle invalid input (non-integer)
            self.current_page_entry.delete(0, customtkinter.END)
            self.current_page_entry.insert(0, str(self.current_page))

    def check_titles_db(self):
        data = self.cache.get_data_from_cache("titleDB")
        if data is None and os.path.exists(os.path.join(self.cache.cache_directory, "files", "titles.US.en.json")):
            self.cache.add_custom_file_to_cache("titleDB", os.path.join(self.cache.cache_directory, "files", "titles.US.en.json"))
            self.define_titles_db()
            return True

        if data:
            if time.time() - data["time"] < 604800:
                return True

            if self.attempted_update:
                self.attempted_update = False
                if messagebox.askyesno("Outdated TitleDB", "The titleDB is outdated. It previously failed to update. Would you like to try again?"):
                    return self.check_titles_db()
                else:
                    self.attempted_update = True
                    return True

            messagebox.showinfo("Outdated TitleDB", "The TitleDB is outdated. It will now be updated. This happens every week.")
            self.attempted_update = True
        else:
            messagebox.showinfo("Missing TitleDB", "The TitleDB is missing. This is used to gather the required metadata for downloading saves and mods. It will now be downloaded.")

        progress_window = ProgressWindow(master=self, title="Downloading TitleDB",)
        Thread(target=self.download_titles_db, args=(progress_window,)).start()

    def download_titles_db(self, progress_window):
        print("Downloading TitleDB...")
        progress_frame = progress_window.progress_frame
        progress_frame.start_download("TitleDB", 0)
        
        response_result = create_get_connection("https://github.com/Viren070/titledb/releases/download/latest/titles.US.en.json", stream=True, headers=get_headers(self.settings.app.token), timeout=30)
        if not all(response_result):
            if not response_result[1] == "Cancelled":
                messagebox.showerror("Download Error", f"There was an error while attempting to download the TitleDB:\n\n {response_result[1]}")
            progress_window.destroy()
            return
        response = response_result[1]
        progress_frame.start_download("TitleDB", int(response.headers.get('content-length', 0)))
        progress_frame.grid(row=0, column=0, sticky="ew")
        download_path = os.path.normpath(os.path.join(os.getcwd(), "titles.US.en.json"))
        download_result = download_through_stream(response, download_path, progress_frame, 1024*128)
        progress_frame.complete_download()
        progress_frame.grid_forget()
        progress_window.destroy()

        if not all(download_result):
            messagebox.showerror("Download Error", f"There was an error while attempting to download the TitleDB:\n\n {download_result[1]}")
            return

        move_to_cache_result = self.cache.add_custom_file_to_cache("titleDB", download_path)
        if not all(move_to_cache_result):
            messagebox.showerror("Download Error", f"There was an error while attempting to add the downloaded database to cache :\n\n {move_to_cache_result[1]}")
            return

        cache_lookup_result = self.cache.get_data_from_cache("titleDB")
        if not cache_lookup_result:
            messagebox.showerror("Download Error", "The TitleDB could not be retrieved from the cache.")
            return

        titleDB_path = cache_lookup_result["data"]
        with open(titleDB_path, "r", encoding="utf-8") as f:
            self.titles_db = json.load(f)
        
        self.define_titles_db()
        messagebox.showinfo("Download Complete", "The TitleDB has been downloaded successfully.")
       

    def download_game(self, game):
        print("looking up game: ", game.get_attribute("name"))
        # remove non ascii characters from game name
        game_name = game.get_attribute("name")
        game_name = ''.join(i for i in game_name if ord(i) < 128)
        game_name = game_name.replace(" ", "+")
        print("normalised name: ", game_name)
        
        if not messagebox.askyesno("Game Search Disclaimer", 
                                   """
                                    PLEASE READ
                                    \n\nThe application will now retrieve a list of websites to search from Viren070/Emulator-Manager-Resources,
                                    \n\nit will then open several tabs in your default browser with the retrieved websites. 
                                    \nI am not responsible for anything that happens outside of the application.
                                    \n\nTIP: I recommend installing uBlock Origin extension and the bypass all shortlinks userscript to avoid any unwanted ads and link shortners.
                                    \n\nWould you like to continue?
                                    """):
            return
        # search for game on the internet
        search_urls = self.get_search_urls()
    
        for url in search_urls:
            open_new_tab(base64.b64decode(url.encode("utf-8")).decode("utf-8") + game_name)
            
    def get_search_urls(self):
        search_urls_location = "https://raw.githubusercontent.com/Viren070/Emulator-Manager-Resources/main/links.txt"
        check_cache = self.cache.get_data_from_cache("game_search_urls")
        if check_cache and time.time() - check_cache["time"] < 604800: # 1 week
            return check_cache["data"]
        
        response_result = create_get_connection(search_urls_location, headers=get_headers(self.settings.app.token), timeout=30)
        if not all(response_result):
            return response_result
        
        response = response_result[1]
        links = response.text.split("\n")
        
        add_to_cache_result = self.cache.add_to_index("game_search_urls", links)
        if not all(add_to_cache_result):
            messagebox.showerror("Cache Error", f"Error adding game search urls to cache:\n\n{add_to_cache_result[1]}")
        
        return links
    def is_update(self, title_id):
        return title_id.endswith('800')

    def is_dlc(self, title_id):
        return not (self.is_update(title_id) or title_id.endswith('000'))

    def is_base(self, title_id):
        return title_id.endswith('000')