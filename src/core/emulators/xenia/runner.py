import os
import platform
import shutil
import subprocess
import time
from pathlib import Path
from zipfile import ZipFile

from core.config import constants
from core.logging.logger import Logger
from core.utils.files import extract_zip_archive_with_progress, copy_directory_with_progress
from core.network.github import get_latest_release_with_asset
from core.network.web import download_file_with_progress


class Xenia:
    def __init__(self, settings, versions):
        self.logger = Logger(__name__).get_logger()
        self.settings = settings
        self.versions = versions
        self.running = False
        self.main_progress_frame = None
        self.data_progress_frame = None

    def get_user_directory(self):
        if self.settings.xenia.release_channel == "master":
            if self.settings.xenia.portable_mode:
                return self.settings.xenia.install_directory / "master"
            match platform.system().lower():
                case "windows":
                    return Path.home() / "Documents" / "Xenia"
        else:
            return self.settings.xenia.install_directory / "canary"

    def get_installed_version(self, release_channel):
        return (self.versions.get_version(f"xenia_{release_channel.lower()}") or "Unknown") if ((self.settings.xenia.install_directory / release_channel.lower() / ("xenia_canary.exe" if release_channel == "canary" else "xenia.exe")).exists()) else ""

    def delete_xenia_zip(self, zip_path):
        time.sleep(2)
        os.remove(zip_path)

    def verify_xenia_zip(self, path_to_archive, release_channel):
        try:
            with ZipFile(path_to_archive, 'r') as archive:
                if ("xenia.exe" if release_channel == "Master" else "xenia_canary.exe") in archive.namelist():
                    return True
                else:
                    return False
        except Exception:
            return False

    def get_xenia_release(self):
        release_channel = self.settings.xenia.release_channel.lower()
        return get_latest_release_with_asset(
            repo_owner=constants.Xenia.GH_CANARY_RELEASE_REPO_OWNER.value if release_channel == "canary" else constants.Xenia.GH_RELEASE_REPO_OWNER.value,
            repo_name=constants.Xenia.GH_CANARY_RELEASE_REPO_NAME.value if release_channel == "canary" else constants.Xenia.GH_RELEASE_REPO_NAME.value,
            regex=constants.Xenia.GH_CANARY_RELEASE_ASSET_REGEX.value if release_channel == "canary" else constants.Xenia.GH_RELEASE_ASSET_REGEX.value,
            token=self.settings.token,
            use_commit_as_version=release_channel == "canary"
        )

    def download_xenia_release(self, release, progress_handler=None):
        return download_file_with_progress(
            download_url=release["download_url"],
            download_path=Path(release["filename"]).resolve(),
            progress_handler=progress_handler,
        )

    def extract_xenia_release(self, release, progress_handler=None):
        if release.suffix != ".zip":
            return {
                    "status": False,
                    "message": "Unsupported archive type",
            }

        return self.extract_xenia_zip_archive(release, progress_handler)

    def extract_xenia_zip_archive(self, release_archive, progress_handler=None):
        return extract_zip_archive_with_progress(
            zip_path=release_archive,
            extract_directory=self.settings.xenia.install_directory / self.settings.xenia.release_channel,
            progress_handler=progress_handler
        )

    def delete_xenia(self):
        release_channel = self.settings.xenia.release_channel
        try:
            path_to_remove = self.settings.xenia.install_directory / release_channel
            shutil.rmtree(path_to_remove)
            return {
                "status": True,
                "message": f"Successfully deleted Xenia {release_channel}",
            }

        except OSError as e:
            return {
                "status": False,
                "message": f"Failed to delete Xenia {release_channel} due to error:\n\n{e}",
            }

    def launch_xenia(self):

        xenia_exe = self.settings.xenia.install_directory / self.settings.xenia.release_channel / ("xenia.exe" if self.settings.xenia.release_channel == "master" else "xenia_canary.exe")
        if not xenia_exe.exists():
            return {
                "run_status": False,
                "message": "Xenia executable does not exist",
            }

        if self.settings.xenia.portable_mode and self.settings.xenia.release_channel == "master":
            (self.settings.xenia.install_directory / "portable.txt").touch()
        else:
            (self.settings.xenia.install_directory / "portable.txt").unlink(missing_ok=True)

        args = [xenia_exe]
        try:
            run = subprocess.run(args, check=False, capture_output=True)
        except Exception as e:
            return {
                "run_status": False,
                "message": f"Failed to launch xenia due to error:\n\n{e}",
            }
        if run.returncode != 0:
            return {
                "run_status": True,
                "error_encountered": True,
                "message": run.stderr.decode("utf-8")
            }
        return {
            "run_status": True,
            "error_encountered": False,
            "message": "Xenia successfully launched and exited with no errors"
        }

    def export_xenia_data(self, export_directory, folders, progress_handler=None):

        user_directory = self.get_user_directory()

        if not user_directory.exists():
            return {
                "status": False,
                "message": f"No xenia data was found. Nothing to export.\n\nPortable: {"True" if self.settings.xenia.portable_mode else "False"}\nUser Directory:{user_directory}"
            }

        return copy_directory_with_progress(
            source_dir=user_directory,
            target_dir=export_directory,
            progress_handler=progress_handler,
            include=folders
        )

    def import_xenia_data(self, import_directory, folders, progress_handler=None):
        user_directory = self.get_user_directory()

        if not user_directory.exists():
            return {
                "status": False,
                "message": f"No xenia data was found. Nothing to import.\n\nPortable: {"True" if self.settings.xenia.portable_mode else "False"}\nUser Directory:{user_directory}"
            }

        return copy_directory_with_progress(
            source_dir=import_directory,
            target_dir=user_directory,
            progress_handler=progress_handler,
            include=folders
        )

    def delete_xenia_data(self, folders_to_delete=None, progress_handler=None):
        user_directory = self.get_user_directory()

        if folders_to_delete is None:
            folders_to_delete = constants.Xenia.USER_FOLDERS.value

        total = len(folders_to_delete)
        progress = 0
        progress_handler.set_total_units(total)
        for folder in folders_to_delete:
            if progress_handler.should_cancel():
                progress_handler.cancel()
                return {
                    "status": False,
                    "message": "Delete operation cancelled"
                }
            path = user_directory / folder
            if not path.exists() or path.name not in constants.Xenia.USER_FOLDERS.value:
                total -= 1
                progress_handler.set_total_units(total)
                continue

            try:
                self.logger.info("Deleting %s", path)
                if path.is_file():
                    path.unlink()
                else:
                    shutil.rmtree(path)
                progress += 1
                progress_handler.report_progress(progress)
            except Exception as error:
                self.logger.error("Delete error: %s", error)
                progress_handler.report_error(error)
                return {
                    "status": False,
                    "message": f"Error while attempting to delete {folder}: {error}"
                }
        progress_handler.report_success()
        return {
            "status": True,
            "message": "Xenia data deleted successfully"
        }
