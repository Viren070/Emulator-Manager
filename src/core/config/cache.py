import json
import shutil
import time
from pathlib import Path

from core.config import constants
from core.config.paths import Paths
from core.logging.logger import Logger


class Cache:
    """
    The Cache class is used to store and retrieve data in the cache directory.

    Methods:
        - is_index_file_valid: Check if the index file is valid.
        - create_index_file: Create the index file.
        - get_data_from_cache: Get data from the cache.
        - add_to_index: Add data to the index file.
        - remove_from_index: Remove data from the index file.
        - add_json_data_to_cache: Add JSON data to the cache.
        - get_json_data_from_cache: Get JSON data from the cache.
        - add_custom_file_to_cache: Add a custom file to the cache.
    """
    def __init__(self, paths: Paths):
        self.logger = Logger(__name__ + "." + self.__class__.__name__).get_logger()
        self.paths = paths
        self.cache_directory = self.paths.cache_dir
        self.cache_directory.mkdir(parents=True, exist_ok=True)
        self.index_file = self.cache_directory / "index.json"

        if not self._is_index_file_valid():
            self._create_index_file()

    def reset(self):
        """
        Reset the cache by removing all files and the index file.
        """
        self.logger.info("Resetting the cache")
        for file in self.cache_directory.iterdir():
            file.unlink()

    def _is_index_file_valid(self):
        """
        Check if the index file is valid.

        Returns:
            bool: True if the index file is valid, False otherwise.
        """
        if not self.index_file.exists():
            return False
        with open(self.index_file, "r", encoding="utf-8") as file:
            try:
                contents = json.load(file)
            except json.JSONDecodeError as error:
                self.logger.error("Index file is not a valid JSON file, full error: %s", error)
                return False
            if contents.get("cache_version") != constants.App.CACHE_VERSION.value:
                self.logger.debug("Cache version mismatch, returning False")
                return False
        return True

    def _create_index_file(self):
        """
        Creates the index file in the cache directory.
        """
        self.logger.info("Creating cache index file")
        self.index_file.parent.mkdir(exist_ok=True)
        with open(self.index_file, "w", encoding="utf-8") as file:
            json.dump({"cache_version": constants.App.CACHE_VERSION.value}, file)

    def _get_index(self):
        """
        Get the index file.

        Returns:
            dict: The contents of the index file.
        """
        with open(self.index_file, "r", encoding="utf-8") as file:
            return json.load(file)

    def _set_index(self, data: dict):
        """
        Set the index file.

        Args:
            data (dict): The data to write to the index file.
        """
        with open(self.index_file, "w", encoding="utf-8") as file:
            json.dump(data, file)

    def _add_path_to_index(self, key: str, path: str, ttl: float):
        """
        Add a given path to the index file.

        Args:
            key (str): The key to store the data under.
            path (str): The path to store with the key.
            ttl (float): The time-to-live for the cache entry.
        """
        if not self._is_index_file_valid():
            self._create_index_file()
            return {
                "status": False,
            }

        index = self._get_index()
        index[key] = {
            "path": str(path),  # Ensure path is stored as a string
            "ttl": ttl,
        }
        self._set_index(index)

    def _get_path_from_index(self, key: str):
        """
        Get a given path from the index file.

        Args:
            key (str): The key to get the path for.

        Returns:
            dict: A dictionary with the status and path.
        """
        if not self._is_index_file_valid():
            self._create_index_file()
            return {
                "status": False,
            }

        index = self._get_index()
        if key not in index:
            self.logger.debug("Key %s not found in cache", key)
            return {
                "status": False,
            }

        data = index.get(key)
        try:
            path = Path(data["path"])
            ttl = data["ttl"]
        except (KeyError, TypeError) as error:
            # index entry is invalid, remove it
            self.logger.error("Data for key %s is invalid: %s", key, error)
            self._remove_from_index(key)
            return {
                "status": False,
            }

        if not path.exists():
            self.logger.debug("Cache file %s does not exist, removing from index", path)
            self._remove_from_index(key)
            return {
                "status": False,
            }

        if path.stat().st_mtime + ttl < time.time():
            self.logger.debug("Cache file %s is older than the ttl, removing", path)
            path.unlink()
            self._remove_from_index(key)
            return {
                "status": False,
            }

        self.logger.debug("Got path from cache under key %s", key)
        return {
            "status": True,
            "path": path,
        }

    def _remove_from_index(self, key: str):
        """
        Remove a given key from the index file.

        Args:
            key (str): The key to remove from the index.
        """
        index = self._get_index()
        index.pop(key, None)  # Use pop with default to avoid KeyError
        self._set_index(index)

    def add_file(self, key: str, file: Path, ttl: float = float("inf")):
        """
        Add a file to the cache directory with the given key and ttl, which defaults to infinity.

        Args:
            key (str): The key to store the file under.
            file (pathlib.Path): The file to store in the cache.
            ttl (float): The time to live for the data in the cache in seconds. Default is infinity.
        """
        if not self._is_index_file_valid():
            self._create_index_file()

        self.logger.debug("Adding file to cache under key %s", key)
        cache_file = self.cache_directory / file.name
        shutil.move(file, cache_file)
        self._add_path_to_index(key, cache_file, ttl)

    def get_file(self, key: str):
        """
        Get a file from the cache directory.

        Args:
            key (str): The key to get the file for.

        Returns:
            dict: A dictionary with the status and path.
        """
        return self._get_path_from_index(key)

    def add_json(self, key: str, data, ttl: float = float("inf")):
        """
        Create a JSON file in the cache directory with the given data.
        Add the key and the path to the index file, with the ttl.

        Args:
            key (str): The key to store the data under.
            data: The data to store in the json file.
            ttl (float): The time to live for the data in the cache in seconds. Default is infinity.
        """
        if not self._is_index_file_valid():
            self._create_index_file()

        self.logger.debug("Adding dictionary to cache under key %s", key)
        cache_file = self.cache_directory / f"{key}.json"
        with open(cache_file, "w", encoding="utf-8") as file:
            json.dump(data, file)

        self._add_path_to_index(key, str(cache_file), ttl)

    def get_json(self, key: str):
        """
        Get a dictionary from the cache. If the data is older than the ttl, it will be removed.

        Args:
            key (str): The key to get the data for.

        Returns:
            dict: A dictionary with the status and data.
        """
        file_info = self._get_path_from_index(key)
        if not file_info["status"]:
            self.logger.debug("Key %s not found in cache", key)
            return {
                "status": False,
            }

        with open(file_info["path"], "r", encoding="utf-8") as file:
            try:
                contents = json.load(file)
            except json.JSONDecodeError as error:
                self.logger.error("Cache file %s is not a valid JSON file, full error: %s", file_info["path"], error)
                return {
                    "status": False,
                }
        self.logger.debug("Got dictionary from cache under key %s", key)
        return {
            "status": True,
            "data": contents,
        }
