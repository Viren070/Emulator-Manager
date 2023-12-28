from threading import Thread
from tkinter import messagebox, filedialog
import os
import json 
import customtkinter
from PIL import Image
import shutil
from gui.windows.progress_window import ProgressWindow
from utils.requests_utils import create_get_connection, get_headers
from utils.downloader import download_file
from threading import Thread

class SwitchTitle:
    def __init__(self, master, title_id, settings, cache):
        self.title_id = title_id
        self.downloading_cover = False
        self.master = master
        self.titles_db = master.titles_db
        self.button = None
        self.settings = settings
        self.cache = cache
        cache_metadata_lookup_result = self.cache.get_cached_data(self.title_id)
        cache_image_lookup_result = self.cache.get_cached_data(f"{self.title_id}-Icon [PATH]")
        if not cache_metadata_lookup_result:
            print("Gathering metadata for title from cached title db:", self.title_id)
            self.title_data = self.gather_metadata()
        else:
            print("Using cached metadata for title:", self.title_id)
            self.title_data = cache_metadata_lookup_result["data"]
        if not cache_image_lookup_result:
            print("Downloading cover for title:", self.title_id)
            image = settings.get_image_path("placeholder_icon")
            Thread(target=self.download_cover, args=(True,)).start()
        else:
            print("Using cached cover for title:", self.title_id)
            image = cache_image_lookup_result["data"]
        self.cover = customtkinter.CTkImage(Image.open(image), size=(224, 224)) 
        

    def gather_metadata(self): 
        if self.titles_db is None:
            return None
        title_data = self.titles_db.get(self.title_id)
        if title_data is None:
            return None 
        self.cache.add_to_index(self.title_id, title_data)
        return title_data
        
    def download_cover(self, skip_prompt=True):
        if self.downloading_cover:  # if currently downloading cover, return
            return

        if not skip_prompt:  # if skip_prompt is False, ask user for confirmation and return if user cancels
            user_confirmation = messagebox.askyesno("Download Cover", "Are you sure you want to download a cover for this game?")
            if not user_confirmation:
                return
        if self.title_data is None:
            if not skip_prompt:
                messagebox.showerror("Download Error", "This game does not have a cover image available.")
            return
        if self.cache.get_cached_data(f"{self.title_id}-Icon [PATH]"):
            if not skip_prompt:
                user_confirmation = messagebox.askyesno("Download Cover", "A cover image already exists for this game. Are you sure you want to download a new one?")
                if not user_confirmation:
                    return
                self.cache.remove_from_index(self.title_id)
            else:
                return
        self.downloading_cover = True
        
        response_result = create_get_connection(self.title_data["iconUrl"], stream=True, headers=get_headers(self.settings.app.token), timeout=30)
        if not all(response_result):
            if not skip_prompt:
                messagebox.showerror("Download Error", f"There was an error while attempting to download the cover image:\n\n {response_result[1]}")
            self.downloading_cover = False
            return
        response = response_result[1]
        download_path = os.path.join(os.getcwd(), f"{self.title_id}.png")
        download_result = download_file(response, download_path)
        if not all(download_result):
            if not skip_prompt:
                messagebox.showerror("Download Error", f"There was an error while attempting to download the cover image:\n\n {download_result[1]}")
            self.downloading_cover = False
            return
        self.cache.move_image_to_cache(f"{self.title_id}-Icon [PATH]", download_path)
        if self.button is not None:
            self.cover = customtkinter.CTkImage(Image.open(self.cache.get_cached_data(f"{self.title_id}-Icon [PATH]")["data"]), size=(224, 224))
            self.button.configure(image=self.cover)
        self.downloading_cover = False
       
        
    def choose_custom_cover(self):
        new_cover = filedialog.askopenfilename(title="Select a new cover image", filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif")])
        if new_cover:
            self.cover = customtkinter.CTkImage(Image.open(new_cover), size=(224, 224))
            if self.button is not None:
                self.button.configure(image=self.cover) 
            else:
                self.master.update_results()
            cache_path = os.path.join(self.cache.cache_directory, "images", f"{self.title_id}.png")
            shutil.copy2(new_cover, cache_path)
class SwitchROMSFrame(customtkinter.CTkFrame):
    def __init__(self, master, settings, cache, get_title_ids_func):
        super().__init__(master, height=700)
        self.get_title_ids = get_title_ids_func
        self.results_per_page = 10
        self.refreshing = False
        self.settings = settings
        self.cache = cache
        self.current_page = None
        self.update_in_progress = False
        self.build_frame()
        title_ids = self.get_title_ids()
        cache_lookup_result = self.cache.get_cached_data("titlesDB [PATH]") # Check if titles.US.en is cached
        missing_title = False
        self.titles_db = None
        if cache_lookup_result is not None and os.path.exists(cache_lookup_result["data"]):
            for title_id in title_ids:
                if not self.cache.get_cached_data(f"{title_id}"):
                    missing_title = True
                    break
            if missing_title:
                with open(cache_lookup_result["data"], "r", encoding="utf-8") as f:
                    print("Loading titles.US.en from cache")
                    self.titles_db = json.load(f)
             
        self.titles = [SwitchTitle(self, title_id, settings, cache) for title_id in title_ids]  # Create game objects
        self.searched_titles = self.titles
        self.total_pages = (len(self.searched_titles) + self.results_per_page - 1) // self.results_per_page
        self.total_pages_label.configure(text=f"/ {self.total_pages}")
        self.update_results()
        
    def refresh_title_list(self):
        if self.refreshing:
            return
        print("REFRESHING...")
        self.refresh_button.configure(state="disabled", text="Refreshing...")
        self.refreshing = True 
        self.check_titles_db()
        self.titles = [SwitchTitle(self, title_id, self.settings, self.cache) for title_id in self.get_title_ids()]  # Create game objects
        self.total_pages = (len(self.searched_titles) + self.results_per_page - 1) // self.results_per_page
        self.total_pages_label.configure(text=f"/ {self.total_pages}")
        self.searched_titles = self.titles 
        self.update_results()
        self.refresh_button.configure(state="normal", text="Refresh")
        self.refreshing = False
        print("REFRESH COMPLETE")
        
   
    def build_frame(self):
        # Create a search bar
        
        self.refresh_frame = customtkinter.CTkFrame(self, corner_radius=50)
        self.refresh_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nw")
        self.refresh_button = customtkinter.CTkButton(self.refresh_frame, text="Refresh", width=100, corner_radius=50, command=self.refresh_title_list)
        self.refresh_button.grid(row=0, column=0, padx=5, pady=5)
        
        search_frame = customtkinter.CTkFrame(self, corner_radius=50)
        search_frame.grid(row=0, column=0, pady=(10,0), padx=10, sticky="ne")

        self.search_entry = customtkinter.CTkEntry(search_frame, placeholder_text="Search")
        self.search_entry.grid(row=0, column=0, padx=10, pady=10, sticky="e")
        self.search_entry.bind("<Return>", self.perform_search)
        self.search_button = customtkinter.CTkButton(search_frame, text="Go", width=60, command=self.perform_search)
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
        self.current_page_entry.grid(row=0, column=0, padx=(10,0), pady=10, sticky="nsew")
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
        self.grid_columnconfigure(1, weight=3)
        self.grid_columnconfigure(2, weight=1)
   

    
    
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
            return
        self.update_in_progress = True
        start_index = (self.current_page - 1) * self.results_per_page
        end_index = (start_index + self.results_per_page) - 1
        for widget in self.result_frame.winfo_children():
            widget.grid_forget()
            
        row_counter = 0
        for i, game in enumerate(self.searched_titles):
            if i > end_index:
                break
            if i < start_index:
                continue
            button = customtkinter.CTkButton(self.result_frame, text="", image=game.cover)
            game.button = button
            button.bind("<Button-3>", command=lambda event, game=game: game.choose_custom_cover())
            button.bind("<Shift-Button-3>", command=lambda event, game=game: game.download_cover())
            button.grid(row=row_counter, column=0, padx=10, pady=5, sticky="w")
            row_counter += 2
        self.current_page_entry.delete(0, customtkinter.END)
        self.current_page_entry.insert(0, str(self.current_page))
        self.next_button.configure(state="normal")
        self.prev_button.configure(state="normal")
        self.update_in_progress = False

    def perform_search(self, *args):
        query = self.search_entry.get()
        if query == "":
            self.searched_titles = self.titles
        else:
            self.searched_titles = []
            for title in self.titles:
                if query.lower() in title.name.lower():
                    self.searched_titles.append(title)
        self.total_pages = (len(self.searched_titles) + self.results_per_page - 1) // self.results_per_page
        self.total_pages_label.configure(text=f"/ {self.total_pages}")
        self.current_page = 1
        self.update_results()

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
        if not os.path.exists(os.path.join(self.cache.cache_directory, "files", "titles.US.en.json")) or self.cache.get_cached_data("titlesDB [PATH]") is None:
            messagebox.showinfo("Missing TitleDB", "The TitleDB is missing. This is used to gather the required metadata for downloading saves and mods. It will now be downloaded.")
        else:
            data = self.cache.get_cached_data("titlesDB [PATH]")
            import time 
            if time.time() - data["time"] < 604800:  # 7 days 
                return 
        progress_window = ProgressWindow(master=self, title="Downloading TitleDB",)
        Thread(target=self.download_titles_db, args=(progress_window,)).start()

    def download_titles_db(self, progress_window):
        progress_frame = progress_window.progress_frame
        progress_frame.start_download("TitleDB", 0)
        progress_frame.cancel_download_button.configure(state="disabled")
        from utils.requests_utils import create_get_connection
        from utils.downloader import download_through_stream
        response_result = create_get_connection("https://github.com/arch-box/titledb/releases/download/latest/titles.US.en.json", stream=True, headers=get_headers(self.settings.app.token), timeout=30)
        if not all(response_result):
            messagebox.showerror("Download Error", f"There was an error while attempting to download the TitleDB:\n\n {response_result[1]}")
            return 
        response = response_result[1]
        progress_frame.start_download("TitleDB", int(response.headers.get('content-length', 0)))
        progress_frame.cancel_download_button.configure(state="disabled")
        progress_frame.grid(row=0, column=0, sticky="ew")
        download_path = os.path.normpath(os.path.join(os.getcwd(), "titles.US.en.json"))
        download_result = download_through_stream(response, download_path, progress_frame, 1024*128)
        progress_frame.complete_download()
        progress_frame.grid_forget()
        progress_window.destroy()
        self.cache.move_file_to_cache("titlesDB [PATH]", download_path)
        with open(self.cache.get_cached_data("titlesDB [PATH]")["data"], "r", encoding="utf-8") as f:
            print("Loading titles.US.en from cache")
            self.titles_db = json.load(f)
        self.refresh_title_list()
        messagebox.showinfo("Download Complete", "The TitleDB has been downloaded successfully.")
        return download_result