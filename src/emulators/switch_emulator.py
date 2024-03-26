import os
import shutil

from zipfile import ZipFile

class SwitchEmulator:
    def __init__(self, emulator, emulator_settings, firmware_path, key_path):
        """_summary_

        Args:
            emulator (str): switch emulator to use
            settings (Settings): settings object
            firmware_path (str): relative path to the firmware directory
            key_path (str): relative path to the key directory
        """
        self.emulator = emulator
        self.emulator_settings = emulator_settings
        self.firmware_path = firmware_path
        self.key_path = key_path
        
    def check_current_firmware(self):
        """Check if the current firmware is present in the firmware directory
        Returns:
            bool: True if the firmware is present, False otherwise
        """
        firmware_directory = os.path.join(self.emulator_settings.user_directory, self.firmware_path)
        if os.path.exists(firmware_directory) and os.listdir(firmware_directory):
            return True
        return False


    def check_current_keys(self):
        """Check if the current keys are present in the key directory

        Returns:
            tuple: A tuple containing two boolean values, the first one indicates if the prod.keys file is present, the second one indicates if the title.keys file is present
        """
        key_directory = os.path.join(self.emulator_settings.user_directory, self.key_path)
        prod_key = os.path.join(key_directory, "prod.keys")
        title_key = os.path.join(key_directory, "title.keys")
        return (os.path.exists(prod_key), os.path.exists(title_key))


    def verify_firmware_archive(self, path_to_archive):
        """Verify if the given archive is a valid firmware archive

        Args:
            path_to_archive (str): The path to the archive to verify

        Returns:
            bool: True if the archive is a valid firmware archive, False otherwise
        """
        archive = path_to_archive
        if not os.path.exists(archive):
            return False
        if not archive.endswith(".zip"):
            return False
        with ZipFile(archive, 'r') as r_archive:
            for filename in r_archive.namelist():
                if not filename.endswith(".nca"):
                    return False
        return True

    def verify_keys(self, path_to_file, check_all=False):
        if not os.path.exists(path_to_file):
            return False
        if path_to_file.endswith(".keys") and (path_to_file.endswith("title.keys") or path_to_file.endswith("prod.keys")):
            return True
        if not path_to_file.endswith(".zip"):
            return False
        with ZipFile(path_to_file, 'r') as archive:
            title_found = False
            prod_found = False
            for filename in archive.namelist():
                if filename == "title.keys":
                    title_found = True
                elif filename == "prod.keys":
                    prod_found = True
                    if not check_all:
                        return True
            return (title_found and prod_found) if check_all else prod_found

    def install_firmware_from_archive(self, firmware_source, progress_frame):
        firmware_directory = os.path.join(self.emulator_settings.user_directory, self.firmware_path)
        if os.path.exists(firmware_directory):
            shutil.rmtree(firmware_directory)
        os.makedirs(firmware_directory, exist_ok=True)
        extracted_files = []
        progress_frame.start_download(os.path.basename(firmware_source), 0)
        progress_frame.complete_download()
        progress_frame.update_status_label("Extracting...")
        progress_frame.grid(row=0, column=0, sticky="ew")
        excluded = []
        try:
            with ZipFile(open(firmware_source, "rb"), 'r') as archive:
                total = len(archive.namelist())
                for entry in archive.infolist():
                    if not (entry.filename.endswith(".nca") or entry.filename.endswith(".nca/00")):
                        continue
                    path_components = entry.filename.replace(".cnmt", "").split("/")
                    nca_id = path_components[-1]
                    if nca_id == "00":
                        nca_id = path_components[-2]
                    if ".nca" not in nca_id:
                        excluded.append(entry.filename)
                        total -= 1
                        continue
                    new_path = os.path.join(firmware_directory, nca_id)
                    if self.emulator == "ryujinx":
                        os.makedirs(new_path, exist_ok=True)
                        with open(os.path.join(new_path, "00"), "wb") as f:
                            f.write(archive.read(entry))
                    elif self.emulator == "yuzu":
                        os.makedirs(firmware_directory, exist_ok=True)
                        with open(new_path, "wb") as f:
                            f.write(archive.read(entry))
                    extracted_files.append(entry.filename)
                    progress_frame.update_extraction_progress(len(extracted_files)/total)
                    
                       

        except Exception as error:
            progress_frame.grid_forget()
            return (False, error)
        progress_frame.grid_forget()
        return (True, excluded)


    def install_keys_from_file(self, key_path):
        target_key_folder = os.path.join(self.emulator_settings.user_directory, self.key_path)
        if not os.path.exists(target_key_folder):
            os.makedirs(target_key_folder)
        target_key_location = os.path.join(target_key_folder, os.path.basename(key_path))
        shutil.copy(key_path, target_key_location)
        return target_key_location


    def install_keys_from_archive(self, key_archive, progress_frame):
        extracted_files = []
        progress_frame.start_download(os.path.basename(key_archive).replace(".zip", ""), 0)
        progress_frame.grid(row=0, column=0, sticky="ew")
        key_directory = os.path.join(self.emulator_settings.user_directory, self.key_path)
        try:
            with ZipFile(key_archive, 'r') as zip_ref:
                total = len(zip_ref.namelist())
                for file_info in zip_ref.infolist():
                    extracted_file_path = os.path.join(key_directory, file_info.filename)
                    os.makedirs(os.path.dirname(extracted_file_path), exist_ok=True)
                    with zip_ref.open(file_info.filename) as source, open(extracted_file_path, 'wb') as target:
                        target.write(source.read())
                    extracted_files.append(file_info.filename)
                    progress_frame.update_extraction_progress(len(extracted_files)/total)
        except Exception as error:
            progress_frame.grid_forget()
            return (False, error)
        progress_frame.grid_forget()
        return (True, extracted_files)
