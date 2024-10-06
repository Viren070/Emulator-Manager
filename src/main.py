import sys

import customtkinter
from cli.emuhaven_cli import EmuHavenCLI
from core.config.assets import Assets
from core.config.cache import Cache
from core.config.paths import Paths
from core.config.settings import Settings
from core.config.versions import Versions
from core.logging.logger import Logger
from gui.emuhaven import EmuHaven

logger = Logger(__name__).get_logger()

if __name__ == "__main__":
    logger.info("Starting the application with arguments: %s", sys.argv[1:])

    paths = Paths()
    settings = Settings(paths)
    versions = Versions(paths)
    cache = Cache(paths)

    args = sys.argv[1:]
    if args:
        logger.info("Starting the application in CLI mode")
        app = EmuHavenCLI(paths=paths, settings=settings, versions=versions, cache=cache)
    else:
        try:
            # attempt to load assets
            assets = Assets(paths)
            assets.define_assets()
        except FileNotFoundError as e:
            # if assets are not found, log error and exit
            logger.error("Failed to load assets: %s", e)
            sys.exit(1)

        # set the appearance mode and colour theme
        theme = settings.colour_theme_path
        dark_mode = settings.dark_mode
        logger.info("Dark: %s", dark_mode)
        logger.info("Theme: %s", theme)
        customtkinter.set_appearance_mode("dark" if dark_mode else "light")
        customtkinter.set_default_color_theme(str(theme))

        # instantiate the application
        logger.info("Building the application")
        app = EmuHaven(
            paths=paths,
            settings=settings,
            versions=versions,
            cache=cache,
            assets=assets
        )

        # call mainloop to start the Tkinter application
        logger.info("Application started")
        app.mainloop()
