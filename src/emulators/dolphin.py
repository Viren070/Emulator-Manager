import os
import re
import shutil
import subprocess
import time
from tkinter import messagebox
from zipfile import ZipFile

import py7zr

from utils.downloader import download_through_stream
from utils.file_utils import copy_directory_with_progress
from utils.requests_utils import (create_get_connection,
                                  get_file_links_from_page, get_headers)


class Dolphin:
    def __init__(self, gui, settings, metadata):
        self.settings = settings
        self.metadata = metadata
        self.gui = gui
        self.running = False
        self.dolphin_is_running = False
        self.main_progress_frame = None
        self.data_progress_frame = None

    def delete_dolphin_zip(self, zip_path):
        time.sleep(2)
        os.remove(zip_path)

    def verify_dolphin_zip(self, path_to_archive):
        if path_to_archive.endswith(".7z"):  # don't know how else to check if its valid for 7z
            return True
        try:
            with ZipFile(path_to_archive, 'r') as archive:
                if 'Dolphin.exe' in archive.namelist():
                    return True
                else:
                    return False
        except Exception:
            return False

    def install_dolphin_handler(self, release_channel=None, path_to_archive=None, updating=False):
        release_archive = path_to_archive
        if release_channel is None and path_to_archive is None:
            raise ValueError("If release channel is None, you must provide a path to archive")
        if path_to_archive is None:
            release_result = self.get_dolphin_release(release_channel)
            if not all(release_result):
                messagebox.showerror("Install Dolphin", f"There was an error while attempting to fetch the latest {release_channel} release of Dolphin:\n\n{release_result[1]}")
                return
            release = release_result[1]
            if updating and release.version == self.metadata.get_installed_version("dolphin"):
                return
            download_result = self.download_release(release)
            if not all(download_result):
                if download_result[1] != "Cancelled":
                    messagebox.showerror("Error", f"There was an error while attempting to download the latest release of Dolphin\n\n{download_result[1]}")
                else:
                    try:
                        os.remove(download_result[2])
                    except Exception as error:
                        messagebox.showwarning("Error", f"Failed to delete file after cancelling due to error below:\n\n{error}")
                return
            release_archive = download_result[1]
        elif not self.verify_dolphin_zip(path_to_archive):
            messagebox.showerror("Error", "The dolphin archive you have provided is invalid. ")
            return
        extract_result = self.extract_release(release_archive)
        if path_to_archive is None and self.settings.app.delete_files == "True":
            os.remove(release_archive)
        if not all(extract_result):
            if extract_result[1] != "Cancelled":
                messagebox.showerror("Extract Error", f"An error occurred while extracting the release: \n\n{extract_result[1]}")
            return
        if path_to_archive is None:
            self.metadata.update_installed_version("dolphin", release.version)
        if not updating:
            messagebox.showinfo("Install Dolphin", f"Dolphin was successfully installed to {self.settings.dolphin.install_directory}")

    def get_dolphin_release(self, release_channel):
        download_page = "https://dolphin-emu.org/download/list/{}/1/"
        match release_channel:
            case "release": 
                download_page = download_page.format("releases")
            case "development": 
                download_page = download_page.format("master")
            case _: 
                raise ValueError("Invalid release channel")
        
        files_result = get_file_links_from_page(download_page, headers=get_headers(), file_ext=".7z")
        if all(files_result):
            files = files_result[1]
            for release in files: 
                if "ARM64" in release.filename:
                    continue 
                else:
                    latest_release = release
                    break
            match = re.search(r"dolphin(?:-master)?-(\d+(?:-\d+)?)", latest_release.filename)
            if match:
                latest_release.version = match.group(1)
            else:
                latest_release.version = "Unknown"
            return (True, latest_release)
        else:
            return files_result

    def download_release(self, release):
        download_folder = os.getcwd()
        download_path = os.path.join(download_folder, f"{release.filename}.7z")
        response_result = create_get_connection(release.url, headers=get_headers(), stream=True, timeout=30)
        if not all(response_result):
            return response_result
        response = response_result[1]
        release.size = int(response.headers.get('content-length', 0))
        self.main_progress_frame.start_download(release.filename, release.size)
        self.main_progress_frame.grid(row=0, column=0, sticky="ew")

        download_result = download_through_stream(response, download_path, self.main_progress_frame, 1024*203)
        self.main_progress_frame.complete_download()
        return download_result

    def extract_release(self, release):
        if release.endswith(".zip"):
            return self.extract_zip_archive(release)
        elif release.endswith(".7z"):
            return self.extract_7z_archive(release)
        else:
            raise Exception

    def extract_7z_archive(self, release_archive):
        self.main_progress_frame.start_download(os.path.basename(release_archive).replace(".7z", ""), 0)
        self.main_progress_frame.complete_download()
        self.main_progress_frame.update_status_label("Extracting... ")
        self.main_progress_frame.cancel_download_button.configure(state="disabled")
        self.main_progress_frame.grid(row=0, column=0, sticky="nsew")
        extracted = True

        try:
            if os.path.exists(self.settings.dolphin.install_directory) and os.listdir(self.settings.dolphin.install_directory):
                self.main_progress_frame.update_status_label("Deleting old installation...")
                shutil.rmtree(self.settings.dolphin.install_directory)
            os.makedirs(self.settings.dolphin.install_directory, exist_ok=True)
            self.main_progress_frame.update_status_label("Extracting (Unable to show progress)...")
            with py7zr.SevenZipFile(release_archive, mode="r") as archive:
                archive.extractall(path=self.settings.dolphin.install_directory)
            parent_folder = self.settings.dolphin.install_directory
            subfolder = os.path.join(self.settings.dolphin.install_directory, "Dolphin-x64")

            contents = os.listdir(subfolder)
            for item in contents:
                item_path = os.path.join(subfolder, item)
                destination_path = os.path.join(parent_folder, item)
                shutil.move(item_path, destination_path)
            os.rmdir(subfolder)
            extracted_files = os.listdir(self.settings.dolphin.install_directory)
            self.main_progress_frame.update_extraction_progress(1)
            self.main_progress_frame.grid_forget()
            if extracted:
                return (True, extracted_files)
            else:
                return (False, "Cancelled")

        except Exception as error:
            self.main_progress_frame.grid_forget()
            return (False, error)

    def extract_zip_archive(self, release_archive):
        self.main_progress_frame.start_download(f"{os.path.basename(release_archive).replace(".zip", "")}", 0)
        self.main_progress_frame.complete_download()
        self.main_progress_frame.update_status_label("Extracting... ")
        self.main_progress_frame.grid(row=0, column=0, sticky="nsew")
        extracted = True
        try:
            with ZipFile(release_archive, 'r') as archive:
                total_files = len(archive.namelist())
                extracted_files = []
                for file in archive.namelist():
                    if self.main_progress_frame.cancel_download_raised:
                        extracted = False
                        break
                    archive.extract(file, self.settings.dolphin.install_directory)
                    extracted_files.append(file)
                    # Calculate and display progress
                    self.main_progress_frame.update_extraction_progress(len(extracted_files) / total_files)
            self.main_progress_frame.grid_forget()
            if extracted:
                return (True, extracted_files)
            else:
                return (False, "Cancelled")
        except Exception as error:
            self.main_progress_frame.grid_forget()
            return (False, error)

    def delete_dolphin(self):
        try:
            shutil.rmtree(self.settings.dolphin.install_directory)
            messagebox.showinfo("Success", "The Dolphin installation was successfully was removed")
        except Exception as e:
            messagebox.showerror("Error", f"There was an error while attempting to delete Dolphin: \n\\n{e}")
            return

    def launch_dolphin_handler(self, release_channel, skip_update=False, wait_for_exit=True):
        if not skip_update:
            self.gui.configure_buttons("disabled", text="Fetching Updates...  ", width=170)
            self.install_dolphin_handler(release_channel, None, True)

        self.gui.configure_buttons("disabled", text="Launched!  ", width=170)
        dolphin_exe = os.path.join(self.settings.dolphin.install_directory, "Dolphin.exe")
        args = [dolphin_exe]
        self.running = True

        if wait_for_exit:
            subprocess.run(args, check=False)
        else:
            subprocess.Popen(args)
        self.running = False

    def export_dolphin_data(self, mode, directory_to_export_to, folders_to_export=None):
        user_directory = self.settings.dolphin.user_directory

        if not os.path.exists(user_directory):
            messagebox.showerror("Missing Folder", "No dolphin data on local drive found")
            return  # Handle the case when the user directory doesn't exist.
        if mode == "All Data":
            copy_directory_with_progress(user_directory, directory_to_export_to, "Exporting All Dolphin Data", self.data_progress_frame)
        elif mode == "Custom":
            if not folders_to_export:
                messagebox.showerror("Missing Folder", "No folders were selected to export")
                return
            copy_directory_with_progress(user_directory, directory_to_export_to, "Exporting All Dolphin Data", self.data_progress_frame, include=folders_to_export)

    def import_dolphin_data(self, mode, directory_to_import_from, folders_to_import=None):
        user_directory = self.settings.dolphin.user_directory

        if not os.path.exists(directory_to_import_from):
            messagebox.showerror("Missing Folder", "No dolphin data associated with your username was found")
            return  # Handle the case when the user directory doesn't exist.
        if mode == "All Data":
            copy_directory_with_progress(directory_to_import_from, user_directory, "Importing All Dolphin Data", self.data_progress_frame)
        elif mode == "Custom":
            if not folders_to_import:
                messagebox.showerror("Missing Folder", "No folders were selected to import")
                return
            copy_directory_with_progress(directory_to_import_from, user_directory, "Importing All Dolphin Data", self.data_progress_frame, include=folders_to_import)

    def delete_dolphin_data(self, mode, folders_to_delete=None):
        result = ""
        user_directory = self.settings.dolphin.user_directory

        def delete_directory(directory):
            if os.path.exists(directory):
                try:
                    shutil.rmtree(directory)
                    return True
                except Exception as error:
                    messagebox.showerror("Delete Dolphin Data", f"Unable to delete \n{directory}\ndue to error:\n\n{error}")
                    return False
            return False
        if mode == "All Data":
            result += f"Data Deleted from {user_directory}\n" if delete_directory(user_directory) else ""
        elif mode == "Custom":
            deleted = False
            for folder in folders_to_delete:
                folder_path = os.path.join(user_directory, folder)
                if os.path.exists(folder_path) and os.path.isdir(folder_path):
                    if delete_directory(folder_path):
                        deleted = True
                        result += f"Data deleted from {folder_path}\n"
                    else:
                        result += f"Deletion failed for {folder_path}\n"
            if not deleted:
                result = ""
        if result:
            messagebox.showinfo("Delete result", result)
        else:
            messagebox.showinfo("Delete result", "Nothing was deleted.")
