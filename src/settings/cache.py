import json
import os
import shutil
import time
from threading import RLock

class Cache:
    def __init__(self, master, settings, metadata):
        self.lock = RLock()
        self.master = master
        self.settings = settings
        self.metadata = metadata
        self.current_cache_version = 2
        if os.path.exists(os.path.join(os.getcwd(), "PORTABLE.txt")):
            self.cache_directory = os.path.join(os.getcwd(), "portable", "cache")
        else:
            self.cache_directory = os.path.join(os.getenv("APPDATA"), "Emulator Manager", "cache")
        if not os.path.exists(self.cache_directory):
            os.makedirs(self.cache_directory)
        self.index_file = os.path.join(self.cache_directory, "index.json")

        if not self.is_index_file_valid():
            self.create_index_file()

    def is_index_file_valid(self):
        with self.lock:
            if not os.path.exists(self.index_file):
                return False
            with open(self.index_file, "r", encoding="utf-8") as file:
                try:
                    contents = json.load(file)
                    if contents.get("cache_version") != self.current_cache_version:
                        return False
                except json.JSONDecodeError:
                    return False
            return True

    def create_index_file(self):
        with self.lock:
            os.makedirs(os.path.dirname(self.index_file), exist_ok=True)
            with open(self.index_file, "w", encoding="utf-8") as file:
                json.dump({"cache_version": 2}, file, indent=4)

    def get_data_from_cache(self, key):
        with self.lock:
            if not self.is_index_file_valid():
                self.create_index_file()
                return None
            with open(self.index_file, "r", encoding="utf-8") as file:
                index = json.load(file)
            data = index.get(key)
            if data is None:
                return None
            try:
                if not os.path.isfile(data["data"]):
                    self.remove_from_index(key)
                    return None
            except TypeError:
                pass 
            
            return data

    def add_to_index(self, key, data):
        with self.lock:
            if not self.is_index_file_valid():
                self.create_index_file()

            with open(self.index_file, "r", encoding="utf-8") as file:
                index = json.load(file)

            index[key] = {
                "data": data,
                "time": time.time()
            }
            try:
                with open(self.index_file, "w", encoding="utf-8") as file:
                    json.dump(index, file, indent=4)
            except Exception as error:
                return (False, error)
            return (True, data)

    def remove_from_index(self, key, delete_data=True):
        print(f"Removing {key} from cache with delete_data={delete_data}")
        with self.lock:
            if not self.is_index_file_valid():
                self.create_index_file()
                return None
            with open(self.index_file, "r", encoding="utf-8") as file:
                index = json.load(file)
            if key in index:
                try:
                    if os.path.isfile(str(index[key]["data"])) and delete_data:
                        print(f"Removing {index[key]['data']} from cache folder")
                        os.remove(index[key]["data"])
                except OSError: 
                    pass
                del index[key]
            with open(self.index_file, "w", encoding="utf-8") as file:
                json.dump(index, file, indent=4)

    def add_json_data_to_cache(self, key, data):
        with self.lock:
            if not self.is_index_file_valid():
                self.create_index_file()
            # create a new file with the data
            path = os.path.join(self.cache_directory, "files", f"{key}.json")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            # write the data to the file
            with open(path, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=4)
            # add the path to the index file
            self.add_to_index(key, path)

    def get_json_data_from_cache(self, key):
        with self.lock:
            if not self.is_index_file_valid():
                self.create_index_file()
                return None
            # get the path from the index file
            data = self.get_data_from_cache(key)
            if data is None:
                return None
            # read the data from the file
            with open(data["data"], "r", encoding="utf-8") as file:
                return {"data": json.load(file), "time": data["time"]}

    def add_custom_file_to_cache(self, key, file_path):
        with self.lock:
            if not self.is_index_file_valid():
                self.create_index_file()
            # declare variable to store the path of the new file
            new_dir = os.path.join(self.cache_directory, "files")
            os.makedirs(new_dir, exist_ok=True)
            path = os.path.join(new_dir, os.path.basename(file_path))
            try:
                shutil.move(file_path, path)
            except OSError as error:
                return (False, error)
            # add this path to the index file with given key
            return self.add_to_index(key, path)

        
