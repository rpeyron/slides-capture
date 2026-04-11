from ctypes import wintypes
from functools import partial
import os
import sys
import webbrowser
import ctypes

import pystray
from PIL import Image
from src.config import CaptureConfig
from src.helpers import local_file


def run_tray(config: CaptureConfig):

    def open_web(icon, _item, config):
        url = "http://" + ("localhost" if config["host"] == "0.0.0.0" else config["host"]) + ":" + str(config["port"])
        webbrowser.open(url, new=2)

    def quit_app(icon, _item, config):
        icon.stop()
        sys.exit(0)

    image = Image.open(local_file("icon.png"),)
    menu = pystray.Menu(
        pystray.MenuItem("Open", partial(open_web, config=config), default=True),
        pystray.MenuItem("Quit", partial(quit_app,config=config)),
    )

    icon = pystray.Icon("pdf-capture", image, "PDF Capture", menu)

    icon.run()