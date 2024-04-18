import os
import sys
import time 

from gui.windows.emulator_manager import EmulatorManager
from settings.app_settings import load_customtkinter_themes
from utils.logger import setup_logger


if __name__ == "__main__":
    logger = setup_logger(__name__)
    logger.info("Starting Emulator Manager")
    if len(sys.argv) > 1:
        logger.info("Running in CLI mode")
        from cli import handle_cli_args
        handle_cli_args(sys.argv[1:])
    else:
        logger.info("Running in GUI mode")
        logger.info("Loading themes and appearance mode")
        s_time = time.time()
        load_customtkinter_themes(os.path.join(os.path.dirname(os.path.realpath(__file__)), "assets", "themes"))
        logger.info("Building GUI")
        App = EmulatorManager(os.path.dirname(os.path.realpath(__file__)))
        logger.info(f"Initialised in {(time.time() - s_time):.4f}s. Running main loop.")
        App.mainloop()
