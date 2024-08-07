import json
import os
import re
import shutil
import subprocess
from tkinter import messagebox
from zipfile import ZipFile

from packaging import version

from emulators.switch_emulator import SwitchEmulator
from utils.downloader import download_through_stream
from utils.file_utils import copy_directory_with_progress
from utils.requests_utils import (create_get_connection, get_headers,
                                  get_release_from_assets)


class Ryujinx(SwitchEmulator):
    def __init__(self, gui, settings, metadata):
        super().__init__(emulator="ryujinx", emulator_settings=settings.ryujinx, firmware_path="bis/system/Contents/registered", key_path="system")
        self.settings = settings
        self.metadata = metadata
        self.gui = gui
        self.main_progress_frame = None
        self.data_progress_frame = None
        self.updating_ea = False
        self.installing_firmware_or_keys = False
        self.running = False

    def verify_ryujinx_zip(self, path_to_archive):
        try:
            with ZipFile(path_to_archive, 'r') as archive:
                if 'publish/Ryujinx.exe' in archive.namelist():
                    return True
                else:
                    return False
        except Exception:
            return False

    def get_latest_release(self):
        response = create_get_connection('https://api.github.com/repos/Ryujinx/release-channel-master/releases/latest', headers=get_headers(self.settings.app.token))
        if not all(response):
            return (False, response[1])
        response = response[1]
        try:
            release_info = json.loads(response.text)
            latest_version = release_info["tag_name"]
            assets = release_info['assets']
        except KeyError:
            return (False, "API Rate Limited")
        release = get_release_from_assets(assets, "win_x64")
        release.version = latest_version
        return (True, release)

    def download_release(self, release):
        response_result = create_get_connection(release.download_url, stream=True, headers=get_headers(self.settings.app.token))
        if not all(response_result):
            return response_result
        response = response_result[1]
        self.main_progress_frame.start_download(f"Ryujinx {release.version}", release.size)
        self.main_progress_frame.grid(row=0, column=0, sticky="ew")
        download_path = os.path.join(os.getcwd(), f"ryujinx-{release.version}-win_x64.zip")
        download_result = download_through_stream(response, download_path, self.main_progress_frame, 1024*203)
        return download_result

    def extract_release(self, zip_path):
        extract_folder = self.settings.ryujinx.install_directory
        extracted_files = []

        self.main_progress_frame.start_download(os.path.basename(zip_path).replace(".zip", ""), 0)
        self.main_progress_frame.complete_download()
        self.main_progress_frame.update_status_label("Extracting... ")
        self.main_progress_frame.grid(row=0, column=0, sticky="ew")
        if os.path.exists(os.path.join(self.settings.ryujinx.install_directory, "publish")):
            self.delete_ryujinx(True)
        try:
            with ZipFile(zip_path, 'r') as archive:
                total_files = len(archive.namelist())
                for file in archive.namelist():
                    if self.main_progress_frame.cancel_download_raised:
                        self.main_progress_frame.grid_forget()
                        return (False, "Cancelled")
                    archive.extract(file, extract_folder)
                    extracted_files.append(file)
                    # Calculate and display progress
                    self.main_progress_frame.update_extraction_progress(len(extracted_files) / total_files)
        except Exception as error:
            self.main_progress_frame.grid_forget()
            return (False, error)
        self.main_progress_frame.grid_forget()
        return (True, extract_folder)

    def install_release_handler(self, updating=False, path_to_archive=None):
        release_archive = path_to_archive
        if path_to_archive is None:
            release_result = self.get_latest_release()
            if not all(release_result):
                messagebox.showerror("Install Ryujinx", f"There was an error while attempting to fetch the latest release of Ryujinx:\n\n{release_result[1]}")
                return
            release = release_result[1]
            if updating and release.version == self.metadata.get_installed_version("ryujinx"):
                return
            download_result = self.download_release(release)
            if not all(download_result):
                if download_result[1] != "Cancelled":
                    messagebox.showerror("Error", f"There was an error while attempting to download the latest release of Ryujinx:\n\n{download_result[1]}")
                else:
                    try:
                        os.remove(download_result[2])
                    except Exception as error:
                        messagebox.showwarning("Error", f"Failed to delete file after cancelling due to error below \n\n {error}")
                return
            release_archive = download_result[1]
        elif not self.verify_ryujinx_zip(path_to_archive):
            messagebox.showerror("Error", "The archive you have provided is invalid")
            return
        extract_result = self.extract_release(release_archive)
        if not all(extract_result):
            if extract_result[1] != "Cancelled":
                messagebox.showerror("Extract Error", f"An error occurred while extracting the release: \n\n{extract_result[1]}")
            elif path_to_archive is None:
                try:
                    os.remove(release_archive)
                except Exception as error:
                    messagebox.showwarning("Error", f"Failed to delete file after cancelling due to error below:\n\n{error}")
            return
        if path_to_archive is None:
            self.metadata.update_installed_version("ryujinx", release.version)
        if path_to_archive is None and self.settings.app.delete_files == "True" and os.path.exists(release_archive):
            os.remove(release_archive)
        if not updating:
            messagebox.showinfo("Install Ryujinx", f"Ryujinx was successfully installed to {extract_result[1]}")

    def delete_ryujinx(self, skip_prompt=False):
        try:
            shutil.rmtree(os.path.join(self.settings.ryujinx.install_directory, "publish"))
            if not skip_prompt:
                messagebox.showinfo("Delete Ryujinx", "Installation of Ryujinx successfully deleted")
        except Exception as error:
            messagebox.showerror("Delete Error", f"An error occured while trying to delete the installation of Ryujinx:\n\n{error}")

    def launch_ryujinx_handler(self, skip_update=False, wait_for_exit=True):
        if not skip_update:
            self.gui.configure_action_buttons("disabled", text="Fetching Updates...")
            self.install_release_handler(True)
        self.check_and_prompt_firmware_keys_install()
        self.gui.configure_action_buttons("disabled", text="Launched!  ")
        ryujinx_exe = os.path.join(self.settings.ryujinx.install_directory, "publish", "Ryujinx.exe")
        args = [ryujinx_exe]
        self.running = True
        if wait_for_exit:
            subprocess.run(args, check=False)
        else:
            subprocess.Popen(args)
        self.running = False

    def check_and_prompt_firmware_keys_install(self):
        # Helper function to get version
        def get_version(key):
            version_str = self.metadata.get_installed_version(key)
            return version.parse(version_str.split(" ")[0]) if version_str not in ["", None] else None

        # Helper function to ask and set task
        def ask_and_set_task(task_key, version, message):
            if messagebox.askyesno("Missing Keys", message):
                install_tasks[task_key] = version

        # Setup a dict containing tasks to be done
        install_tasks = {"keys": None, "firmware": None}

        # Get installed version of firmware and keys
        installed_firmware_version = get_version("ryujinx_firmware")
        installed_keys_version = get_version("ryujinx_keys")

        # Get latest available common version release
        latest_release = self.get_latest_common_firmware_keys_version()
        # If keys is missing, prompt to install keys
        if not self.check_current_keys()["prod.keys"]:
            ask_and_set_task("keys", str(latest_release) if installed_firmware_version is None else str(installed_firmware_version), "It seems you are missing the switch decryption keys. These keys are required to emulate games. Would you like to install them right now?")

        # If no firmware tasks yet, and no firmware is installed, and the user has not been asked to install firmware yet, prompt to install firmware
        if install_tasks.get("firmware") is None and installed_firmware_version is None and self.settings.app.ask_firmware.lower() == "true":
            ask_and_set_task("firmware", str(latest_release) if installed_keys_version is None else str(installed_keys_version), "It seems you are missing the switch firmware files. Without these files, some games may not run.\n\nWould you like to install the firmware now? If you select no, you will not be asked again")
        else:
            # If user rejects, don't ask again
            self.settings.app.ask_firmware = "False"
            self.settings.update_file()

        # If installed firmware version does not match installed keys version, prompt to install matching versions
        if installed_firmware_version != installed_keys_version:
            if messagebox.askyesno("Error", "It seems that the installed firmware and keys versions do not match. This may cause issues. \n\nWould you like to install the keys and firmware for the same version? The highest version currently installed will be used or the latest available version if that fails."):
                max_version = max([installed_firmware_version, installed_keys_version], default=None)
                install_tasks["keys"] = str(max_version) if max_version is not None else latest_release
                install_tasks["firmware"] = str(max_version) if max_version is not None else latest_release

        # If no tasks, return
        if all(task is None for task in install_tasks.values()):
            return

        # If keys task is not None, install keys
        if install_tasks.get("keys") is not None:
            # Get key release
            key_release = self.get_key_release(install_tasks["keys"])
            # if key release is None and firmware is currently installed
            if key_release is None and installed_firmware_version is not None:
                if messagebox.askyesno("Error", "Failed to find the keys for the currently installed firmware version. Would you like to install the keys and firmware for latest instead"):
                    install_tasks["keys"] = str(latest_release) if str(installed_firmware_version) != latest_release else None
                    install_tasks["firmware"] = str(latest_release) if str(installed_firmware_version) != latest_release else None
                    key_release = self.get_key_release(str(latest_release))
                    firmware_release = self.get_firmware_release(str(latest_release))
                else:
                    install_tasks["keys"] = None

        # If firmware task is not None, install firmware
        if install_tasks.get("firmware") is not None:
            firmware_release = self.get_firmware_release(install_tasks["firmware"])
            if firmware_release is None and installed_keys_version is not None:
                if messagebox.askyesno("Error", "Failed to find the firmware for the currently installed keys version. Would you like to install the keys and firmware for latest instead"):
                    install_tasks["firmware"] = str(latest_release) if str(installed_keys_version) != latest_release else None
                    install_tasks["keys"] = str(latest_release) if str(installed_keys_version) != latest_release else None
                    firmware_release = self.get_firmware_release(str(latest_release))
                    key_release = self.get_key_release(str(latest_release))
                else:
                    install_tasks["firmware"] = None

        # Install keys and firmware if tasks are set
        if install_tasks.get("keys") is not None and install_tasks.get("keys") != str(installed_keys_version):
            if key_release is None:
                messagebox.showerror("Error", "An unexpected error occurred while trying to fetch the keys release. Please try again later.")
            else:
                self.install_key_handler("release", key_release, skip_prompt=True)

        if install_tasks.get("firmware") is not None and install_tasks.get("firmware") != str(installed_firmware_version):
            if firmware_release is None:
                messagebox.showerror("Error", "An unexpected error occurred while trying to fetch the firmware release. Please try again later.")
            else:
                self.install_firmware_handler("release", firmware_release, skip_prompt=True)
    
    def get_key_release(self, version):
        firmware_keys_frame = self.gui.firmware_keys_frame
        if not firmware_keys_frame.versions_fetched():
            firmware_keys_frame.fetch_firmware_and_key_versions()
        keys_dict = firmware_keys_frame.firmware_key_version_dict.get("keys", {})
        return keys_dict.get(version, None)
            
    def get_firmware_release(self, version):
        firmware_keys_frame = self.gui.firmware_keys_frame
        if not firmware_keys_frame.versions_fetched():
            firmware_keys_frame.fetch_firmware_and_key_versions()
        firmware_dict = firmware_keys_frame.firmware_key_version_dict.get("firmware", {})
        return firmware_dict.get(version, None)
    
    def get_latest_common_firmware_keys_version(self):
        firmware_keys_frame = self.gui.firmware_keys_frame
        if not firmware_keys_frame.versions_fetched():
            firmware_keys_frame.fetch_firmware_and_key_versions()
        return firmware_keys_frame.get_latest_common_version()
        

    def install_firmware_handler(self, mode, path_or_release, skip_prompt=False):
        if not skip_prompt and self.check_current_firmware() and not messagebox.askyesno("Firmware Exists", "It seems that you already have firmware installed. Would you like to continue?"):
            return
        if mode == "release":
            release = path_or_release
            firmware_path = self.download_firmware_archive(release)
            if not all(firmware_path):
                if firmware_path[1] != "Cancelled":
                    messagebox.showerror("Download Error", firmware_path[1])
                else:
                    try:
                        os.remove(firmware_path[2])
                    except Exception as error:
                        messagebox.showwarning("Error", f"Failed to delete file after cancelling due to error below:\n\n{error}")
                return False
            firmware_path = firmware_path[1]
            version = release.version
        elif mode == "path" and not self.verify_firmware_archive(path_or_release):
            messagebox.showerror("Error", "The firmware archive you have provided is invalid")
            return
        else:
            firmware_path = path_or_release
        result = self.install_firmware_from_archive(firmware_path, self.main_progress_frame)
        if not result[0]:
            messagebox.showerror("Extract Error", f"There was an error while trying to extract the firmware archive: \n\n{result[1]}")
            return
        result = result[1]
        if mode == "release":
            if self.settings.app.delete_files == "True" and os.path.exists(firmware_path):
                try:
                    os.remove(firmware_path)
                except PermissionError as error:
                    messagebox.showerror("Error", f"Failed to delete firmware archive due to error below \n\n{error}")
            self.metadata.update_installed_version("ryujinx_firmware", version)
        else:
            self.metadata.update_installed_version("ryujinx_firmware", version)
        if result:
            messagebox.showwarning("Unexpected Files", f"These files were skipped in the extraction process: {result}")
        messagebox.showinfo("Firmware Install", "The switch firmware files were successfully installed")
        self.gui.fetch_versions()
        return True

    def download_firmware_archive(self, release):
        firmware = release

        response_result = create_get_connection(firmware.download_url, stream=True, headers=get_headers(self.settings.app.token), timeout=30)
        if not all(response_result):
            return response_result

        response = response_result[1]
        self.main_progress_frame.start_download(f"Firmware {firmware.version}", firmware.size)
        self.main_progress_frame.grid(row=0, column=0, sticky="ew")
        download_path = os.path.join(os.getcwd(), f"Firmware {firmware.version}.zip")
        download_result = download_through_stream(response, download_path, self.main_progress_frame, 1024*203)
        self.main_progress_frame.complete_download()
        return download_result

    def install_key_handler(self, mode, path_or_release, skip_prompt=False):
        if not skip_prompt and self.check_current_keys()["prod.keys"] and not messagebox.askyesno("Keys Exist", "It seems that you already have the decryption keys installed. Would you like to continue?"):
            return
        if mode == "release":
            release = path_or_release
            key_path = self.download_key_archive(release)
            if not all(key_path):
                if key_path[1] != "Cancelled":
                    messagebox.showerror("Download Error", key_path[1])
                else:
                    try:
                        os.remove(key_path[2])
                    except Exception as error:
                        messagebox.showwarning("Error", f"Failed to delete file after cancelling due to below error:\n\n{error}")
                return False
            key_path = key_path[1]
            version = release.version

        elif not self.verify_key_archive(path_or_release):
            messagebox.showerror("Error", "The key archive or file you have provided is invalid. \nPlease ensure that it is a .zip file containing the 'prod.keys' or 'title.keys' in the root directory\nor a 'prod.keys' or 'title.keys' file.")
            return
        else:
            key_path = path_or_release

        if key_path.endswith(".keys"):
            self.install_keys_from_file(key_path)
        else:
            result = self.install_keys_from_archive(key_path, self.main_progress_frame)
            if not all(result):
                messagebox.showerror("Extract Error", f"There was an error while trying to extract the key archive: \n\n{result[1]}")
                return
            result = result[1]
            if "prod.keys" not in result:
                messagebox.showwarning("Keys", "Was not able to find any prod.keys within the archive, the archive was still extracted successfully.")
                return False
        if mode == "release":
            if self.settings.app.delete_files == "True" and os.path.exists(key_path):
                os.remove(key_path)
            self.metadata.update_installed_version("ryujinx_keys", version)
        else:
            self.metadata.update_installed_version("ryujinx_keys", "")
        messagebox.showinfo("Keys", "Decryption keys were successfully installed!")
        self.gui.fetch_versions()
        return True

    def download_key_archive(self, release):
        key = release
        response_result = create_get_connection(key.download_url, stream=True, headers=get_headers(self.settings.app.token), timeout=30)
        if not all(response_result):
            return response_result
        response = response_result[1]
        self.main_progress_frame.start_download(f"Keys {key.version}", key.size)
        self.main_progress_frame.grid(row=0, column=0, sticky="ew")
        download_path = os.path.join(os.getcwd(), f"Keys {key.version}.zip")
        download_result = download_through_stream(response, download_path, self.main_progress_frame, 1024*128)
        self.main_progress_frame.complete_download()
        return download_result

    def export_ryujinx_data(self, mode, directory_to_export_to, folders=None):
        user_directory = self.settings.ryujinx.user_directory
        if not os.path.exists(user_directory):
            messagebox.showerror("Missing Folder", "No Ryujinx data on local drive found")
            return  # Handle the case when the user directory doesn't exist.

        if mode == "All Data":
            copy_directory_with_progress(user_directory, directory_to_export_to, "Exporting All Ryujinx Data", self.data_progress_frame)
        elif mode == "Save Data":
            save_dir = os.path.join(user_directory, 'bis', 'user', 'save')
            copy_directory_with_progress(save_dir, os.path.join(directory_to_export_to, 'bis', 'user', 'save'), "Exporting Ryujinx Save Data", self.data_progress_frame)
        elif mode == "Custom...":
            copy_directory_with_progress(user_directory, directory_to_export_to, "Exporting Custom Ryujinx Data", self.data_progress_frame, include=folders)
        else:
            messagebox.showerror("Error", f"An unexpected error has occured, {mode} is an invalid option.")

    def import_ryujinx_data(self, mode, directory_to_import_from, folders=None):
        user_directory = self.settings.ryujinx.user_directory
        if not os.path.exists(directory_to_import_from):
            messagebox.showerror("Missing Folder", "No Ryujinx data associated with your username found")
            return
        if mode == "All Data":
            copy_directory_with_progress(directory_to_import_from, user_directory, "Import All Ryujinx Data", self.data_progress_frame)
        elif mode == "Save Data":
            save_dir = os.path.join(directory_to_import_from, 'bis', 'user', 'save')
            copy_directory_with_progress(save_dir, os.path.join(user_directory, 'bis', 'user', 'save'), "Importing Ryujinx Save Data", self.data_progress_frame)
        elif mode == "Custom...":
            copy_directory_with_progress(directory_to_import_from, user_directory, "Import All Ryujinx Data", self.data_progress_frame, include=folders)
        else:
            messagebox.showerror("Error", f"An unexpected error has occured, {mode} is an invalid option.")

    def delete_ryujinx_data(self, mode, folders=None):
        result = ""

        user_directory = self.settings.ryujinx.user_directory

        def delete_directory(directory):
            if os.path.exists(directory):
                try:
                    shutil.rmtree(directory)
                    return True
                except Exception as error:
                    messagebox.showerror("Delete Ryujinx Data", f"Unable to delete {directory}:\n\n{error}")
                    return False
            return False

        if mode == "All Data":
            result += f"Data Deleted from {user_directory}\n" if delete_directory(user_directory) else ""
        elif mode == "Save Data":
            save_dir = os.path.join(user_directory, 'bis', 'user', 'save')
            result += f"Data deleted from {save_dir}\n" if delete_directory(save_dir) else ""
        elif mode == "Custom...":
            deleted = False
            for folder in folders:
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
        self.gui.configure_data_buttons(state="normal")
