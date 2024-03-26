import json
import os
import re
import shutil
import subprocess
from tkinter import messagebox
from zipfile import ZipFile

from emulators.switch_emulator import SwitchEmulator
from utils.downloader import download_through_stream
from utils.file_utils import copy_directory_with_progress
from utils.requests_utils import (create_get_connection, get_headers,
                                  get_release_from_assets)


class Yuzu(SwitchEmulator):
    def __init__(self, gui, settings, metadata):
        super().__init__(emulator="yuzu", emulator_settings=settings.yuzu, firmware_path="nand/system/Contents/registered", key_path="keys")
        self.settings = settings
        self.metadata = metadata
        self.gui = gui
        self.main_progress_frame = None
        self.data_progress_frame = None
        self.updating_ea = False
        self.installing_firmware_or_keys = False
        self.running = False

    def verify_yuzu_zip(self, path_to_archive, release_type):
        try:
            with ZipFile(path_to_archive, 'r') as archive:
                if (release_type == "mainline" and 'yuzu-windows-msvc/yuzu.exe' in archive.namelist()) or (release_type == "early_access" and "yuzu-windows-msvc-early-access/yuzu.exe" in archive.namelist()):
                    return True
                else:
                    return False
        except Exception:
            return False

    def delete_early_access(self, skip_prompt=False):
        try:
            shutil.rmtree(os.path.join(self.settings.yuzu.install_directory, "yuzu-windows-msvc-early-access"))
            if not skip_prompt:
                messagebox.showinfo("Success", "The installation of yuzu EA was successfully deleted!")
            return (True, "Success")
        except Exception as error_msg:
            messagebox.showerror("Delete Error", f"Failed to delete yuzu-ea: \n\n{error_msg}")
            return (False, error_msg)

    def get_latest_release(self, release_type):
        response = create_get_connection('https://api.github.com/repos/pineappleEA/pineapple-src/releases/latest' if release_type == "early_access" else "https://api.github.com/repos/yuzu-emu/yuzu-mainline/releases/latest", headers=get_headers(self.settings.app.token))
        if not all(response):
            return (False, response[1])
        response = response[1]
        try:
            release_info = json.loads(response.text)
            latest_version = release_info["tag_name"].split("-")[-1]
            assets = release_info['assets']
        except KeyError:
            return (False, "API Rate Limited")
        release = get_release_from_assets(assets, "Windows" if release_type == "early_access" else "yuzu-windows-msvc-{}.zip", False if release_type == "early_access" else True)
        release.version = latest_version
        return (True, release)

    def download_release(self, release, release_type):
        response_result = create_get_connection(release.download_url, stream=True, headers=get_headers(self.settings.app.token))
        if not all(response_result):
            return response_result
        response = response_result[1]
        download_title = f"{{}} {release.version}".format("Yuzu" if release_type == "mainline" else "Yuzu EA")
        self.main_progress_frame.start_download(download_title, release.size)
        self.main_progress_frame.grid(row=0, column=0, sticky="ew")
        download_path = os.path.join(os.getcwd(), f"Yuzu-{release.version}.zip" if release_type == "mainline" else f"Yuzu-EA-{release.version}.zip")
        download_result = download_through_stream(response, download_path, self.main_progress_frame, 1024*203)
        return download_result

    def extract_release(self, zip_path, release_type):
        extract_folder = self.settings.yuzu.install_directory
        extracted_files = []

        self.main_progress_frame.start_download(os.path.basename(zip_path).replace(".zip", ""), 0)
        self.main_progress_frame.complete_download()
        self.main_progress_frame.update_status_label("Extracting... ")
        self.main_progress_frame.grid(row=0, column=0, sticky="ew")
        if os.path.exists(os.path.join(self.settings.yuzu.install_directory, "yuzu-windows-msvc" if release_type == "mainline" else "yuzu-windows-msvc-early-access")):
            delete_func = self.delete_mainline if release_type == "mainline" else self.delete_early_access
            result = delete_func(True)
            if not all(result):
                return (False, "Failed to delete old installation")
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

    def install_release_handler(self, release_type, updating=False, path_to_archive=None):
        release_archive = path_to_archive
        if path_to_archive is None:
            release_result = self.get_latest_release(release_type)
            if not all(release_result):
                messagebox.showerror("Install Yuzu", f"There was an error while attempting to fetch the latest release of Yuzu:\n\n{release_result[1]}")
                return
            release = release_result[1]
            if updating and release.version == self.metadata.get_installed_version(release_type):
                return
            download_result = self.download_release(release, release_type)
            if not all(download_result):
                if download_result[1] != "Cancelled":
                    messagebox.showerror("Error", f"There was an error while attempting to download the latest release of yuzu {release_type.replace('_', ' ').title()}:\n\n{download_result[1]}")
                else:
                    try:
                        os.remove(download_result[2])
                    except Exception as error:
                        messagebox.showwarning("Error", f"Failed to delete the file after cancelling due to error below:\n\n{error}")
                return
            release_archive = download_result[1]
        elif not self.verify_yuzu_zip(path_to_archive, release_type):
            messagebox.showerror("Error", "The archive you have provided is invalid")
            return
        extract_result = self.extract_release(release_archive, release_type)
        if not all(extract_result):
            if extract_result[1] != "Cancelled":
                messagebox.showerror("Extract Error", f"An error occurred while extracting the release: \n\n{extract_result[1]}")
            elif path_to_archive is None:
                try:
                    os.remove(release_archive)
                except Exception as error:
                    messagebox.showwarning("Error", f"Failed to delete the file after cancelling due to error below:\n\n{error}")
            return
        if path_to_archive is None:
            self.metadata.update_installed_version(release_type, release.version)
        if path_to_archive is None and self.settings.app.delete_files == "True" and os.path.exists(release_archive):
            os.remove(release_archive)
        if not updating:
            messagebox.showinfo("Install Yuzu", f"Yuzu was successfully installed to {extract_result[1]}")

    def launch_yuzu_installer(self):
        path_to_installer = self.settings.yuzu.installer_path
        self.running = True
        subprocess.run([path_to_installer], check=False)
        self.running = False

    def delete_mainline(self, skip_prompt=False):
        try:
            shutil.rmtree(os.path.join(self.settings.yuzu.install_directory, "yuzu-windows-msvc"))
            if not skip_prompt:
                messagebox.showinfo("Delete Yuzu", "Installation of yuzu successfully deleted")
            return (True, "Success")
        except Exception as error:
            messagebox.showerror("Delete Error", f"An error occured while trying to delete the installation of yuzu:\n\n{error}")
            return (False, error)

    def launch_yuzu_handler(self, release_type, skip_update=False, wait_for_exit=True):
        if not skip_update and self.settings.yuzu.use_yuzu_installer != "True":
            func = self.gui.configure_mainline_buttons if release_type == "mainline" else self.gui.configure_early_access_buttons
            func("disabled", text="Fetching Updates...  ")
            self.install_release_handler(release_type, True)
        if release_type == "mainline":
            self.gui.configure_mainline_buttons("disabled", text="Launching...  ")
            yuzu_folder = "yuzu-windows-msvc"
        elif release_type == "early_access":
            self.gui.configure_early_access_buttons("disabled", text="Launching...  ")
            yuzu_folder = "yuzu-windows-msvc-early-access"
        self.verify_and_install_firmware_keys()
        func_to_call = self.gui.configure_mainline_buttons if release_type == "mainline" else self.gui.configure_early_access_buttons
        func_to_call("disabled", text="Launched!  ")
        yuzu_exe = os.path.join(self.settings.yuzu.install_directory, yuzu_folder, "yuzu.exe")
        maintenance_tool = os.path.join(self.settings.yuzu.install_directory, "maintenancetool.exe")
        use_installer = self.settings.yuzu.use_yuzu_installer == "True"

        if use_installer and not skip_update and not os.path.exists(maintenance_tool):
            messagebox.showerror("Error", "The update tool 'maintenancetool.exe' was not found, and it's required to update yuzu as the yuzu installer option is enabled. Please install yuzu first through the installer before launching it.")
            args = [yuzu_exe]
        else:
            args = [maintenance_tool, "--launcher", yuzu_exe] if use_installer and not skip_update else [yuzu_exe]

        self.running = True
        if wait_for_exit:
            subprocess.run(args, check=False)
        else:
            subprocess.Popen(args)
        self.running = False

    def verify_and_install_firmware_keys(self):
        installed_firmware_version = re.compile(r'(\d+\.\d+\.\d+)').findall(self.metadata.get_installed_version("yuzu_firmware"))
        if not installed_firmware_version:
            installed_firmware_version = ""
        else:
            installed_firmware_version = installed_firmware_version[0]
        if installed_firmware_version != "" and self.metadata.get_installed_version("yuzu_keys") != "" and installed_firmware_version != self.metadata.get_installed_version("yuzu_keys"):
            messagebox.showwarning("Version Mismatch", "It seems you have a different version for your keys and firmware. This may cause issues and it is recommended that you install the same version.")
        if not self.check_current_keys()[0]:
            if messagebox.askyesno("Missing Keys", "It seems you are missing the switch decryption keys. These keys are required to emulate games. Would you like to install them right now?"):
                if self.gui.firmware_keys_frame.key_option_menu.cget("state") == "disabled":
                    messagebox.showerror("Install Keys", "Unable to fetch latest prod.keys. Please try again later or restart the application.")
                else:
                    latest_key_release = self.gui.firmware_keys_frame.firmware_key_version_dict["keys"][self.gui.firmware_keys_frame.key_option_menu.cget("values")[0]]
                    self.install_key_handler("release", latest_key_release)
        if self.settings.app.ask_firmware != "False" and not self.check_current_firmware():
            if messagebox.askyesno("Firmware Missing", "It seems you are missing the switch firmware files. Without these files, some games may not run.\n\nWould you like to install the firmware now? If you select no, you will not be asked again"):
                if self.gui.firmware_keys_frame.firmware_option_menu.cget("state") == "disabled":
                    messagebox.showerror("Install Firmware", "Unable to fetch latest Firmware. Please try again later or restart the application.")
                else:
                    latest_firmware_release = self.gui.firmware_keys_frame.firmware_key_version_dict["firmware"][self.gui.firmware_keys_frame.key_option_menu.cget("values")[0]]
                    self.install_firmware_handler("release", latest_firmware_release)
            else:
                self.settings.app.ask_firmware = "False"
                self.settings.update_file()
        return True

    def install_firmware_handler(self, mode, path_or_release):
        if self.check_current_firmware() and not messagebox.askyesno("Firmware Exists", "It seems that you already have firmware installed. Would you like to continue?"):
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
                        messagebox.showwarning("Error", f"Failed to delete the file after cancelling due to error below:\n\n{error}")
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
                    messagebox.showerror("Error", f"Failed to delete firmware archive after installing due to error below: \n\n{error}")
            self.metadata.update_installed_version("yuzu_firmware", version)
        else:
            self.metadata.update_installed_version("yuzu_firmware", "")
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

    def install_key_handler(self, mode, path_or_release):
        if self.check_current_keys()[0] and not messagebox.askyesno("Keys Exist", "It seems you already have decryption keys. Would you like to continue?"):
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
                        messagebox.showwarning("Error", f"Failed to delete the file after cancelling due to error below:\n\n{error}")
                return False
            key_path = key_path[1]
            version = release.version

        elif not self.verify_keys(path_or_release):
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
            self.metadata.update_installed_version("yuzu_keys", version)
        else:
            self.metadata.update_installed_version("yuzu_keys", "")
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

    def export_yuzu_data(self, mode, directory_to_export_to, folders=None):
        user_directory = self.settings.yuzu.user_directory
        if not os.path.exists(user_directory):
            messagebox.showerror("Missing Folder", "No yuzu data on local drive found")
            return  # Handle the case when the user directory doesn't exist.

        if mode == "All Data":
            copy_directory_with_progress(user_directory, directory_to_export_to, "Exporting All Yuzu Data", self.data_progress_frame)
        elif mode == "Save Data":
            save_dir = os.path.join(user_directory, 'nand', 'user', 'save')
            copy_directory_with_progress(save_dir, os.path.join(directory_to_export_to, 'nand', 'user', 'save'), "Exporting Yuzu Save Data", self.data_progress_frame)
        elif mode == "Custom...":
            copy_directory_with_progress(user_directory, directory_to_export_to, "Exporting Custom Yuzu Data", self.data_progress_frame, include=folders)
        else:
            messagebox.showerror("Error", f"An unexpected error has occured, {mode} is an invalid option.")

    def import_yuzu_data(self, mode, directory_to_import_from, folders=None):
        user_directory = self.settings.yuzu.user_directory
        if not os.path.exists(directory_to_import_from):
            messagebox.showerror("Missing Folder", "No yuzu data associated with your username found")
            return
        if mode == "All Data":
            copy_directory_with_progress(directory_to_import_from, user_directory, "Import All Yuzu Data", self.data_progress_frame)
        elif mode == "Save Data":
            save_dir = os.path.join(directory_to_import_from, 'nand', 'user', 'save')
            copy_directory_with_progress(save_dir, os.path.join(user_directory, 'nand', 'user', 'save'), "Importing Yuzu Save Data", self.data_progress_frame)
        elif mode == "Custom...":
            copy_directory_with_progress(directory_to_import_from, user_directory, "Import Custom", self.data_progress_frame, include=folders)
        else:
            messagebox.showerror("Error", f"An unexpected error has occured, {mode} is an invalid option.")

    def delete_yuzu_data(self, mode, folders=None):
        result = ""

        user_directory = self.settings.yuzu.user_directory

        def delete_directory(directory):
            if os.path.exists(directory):
                try:
                    shutil.rmtree(directory)
                    return True
                except Exception as error:
                    messagebox.showerror("Delete Yuzu Data", f"Unable to delete {directory}:\n\n{error}")
                    return False
            return False

        if mode == "All Data":
            result += f"Data Deleted from {user_directory}\n" if delete_directory(user_directory) else ""
        elif mode == "Save Data":
            save_dir = os.path.join(user_directory, 'nand', 'user', 'save')
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
