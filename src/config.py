
from typing import Literal, NotRequired, TypedDict
from selenium.webdriver.common.keys import Keys

from src.helpers import local_file

KEY_NAMES = {
    "left":  Keys.LEFT,
    "right": Keys.RIGHT,
    "up":    Keys.UP,
    "down":  Keys.DOWN,
    "enter": Keys.ENTER,
    "tab":   Keys.TAB,
    "space": Keys.SPACE,
    "escape": Keys.ESCAPE,
    "pageup":     Keys.PAGE_UP,
    "pagedown":   Keys.PAGE_DOWN,    
}
KeyChoice = Literal[*KEY_NAMES] 

# Configurable parameters types

# Selectors types
Selectors = TypedDict(
    "Selectors",
    {
        "prev_button": str,
        "next_button": str,
        "image": str,
        "title": str,
        "pagination": str,
    },
)

Keys = TypedDict(
    "Keys",
    {
        "prev": KeyChoice,
        "next": KeyChoice,
    },
)

# Site configuration 
Site = TypedDict(
    "Site",
    {
        "name": str,
        "url_contains": NotRequired[str],  # Optional pattern to match URLs; if not provided, this site is default
        "url_pattern": NotRequired[str],  # Optional regex pattern to match URLs; if not provided, this site is default
        "keys": NotRequired[Keys],  # Optional key mappings; if not provided, defaults are used
        "selectors": Selectors,  # Seules les clés décrites ci‑dessus sont autorisées
        "hide": list[str],  # Optional list of CSS selectors to hide before capture
    },
)

# Engine configuration
Engine = TypedDict(
    "Engine",
    {
        "headless": bool,
        "selenium_url": NotRequired[None | str],
    },
)

# Le seul type nommé haut‑niveau que tu utilises
CaptureConfig = TypedDict(
    "CaptureConfig",
    {
        "config": str,                           # Path to JSON config file with configuration
        "host": str,                               # Host
        "port": int,                               # Port   
        "delay_after_click": NotRequired[float],  # Delay after clicking next/prev button (default: 0.5s)
        "max_pages": NotRequired[None | int],  # None means capture all pages; int limits page count
        "output_path": str,                    # Directory to save the PDF; default is 'out'
        "output": str,                         # Output PDF filename; if empty, uses title or default
        "default_output": str,                 # Default PDF filename if none found
        "url": str,                            # Default slideshow URL to capture
        "engine": Engine,                      # Engine options
        "sites": list[Site],                   # List of sites; each must have exactly name, url_pattern, selectors
    },
)


DEFAULT_CONFIG_FILE = local_file("config.json")

# Default Config
DEFAULT_CONFIG : CaptureConfig= {
    "config": DEFAULT_CONFIG_FILE,
    "host": "0.0.0.0",
    "port": 4202,
    # Delay after clicking next/prev button (default: 0.5s)
    "delay_after_click": 2,
    # Maximum number of pages to capture (None for all)
    "max_pages": None, 
    # Output path
    "output_path": local_file("out"),
    # Output PDF file name (if None, uses title or default)
    "output": None,
    # Default PDF file name if none found
    "default_output": "slides-images.pdf",
    # Default URL of the slideshow to capture
    "url": "",
    # Run Chrome in headless mode
    "engine": {
        "headless": False,
        "selenium_url": None 
    },
    "sites": [{
        "name": "Canva",
        "url_contains": "canva.com",
        "keys": {
            "prev": "left",
            "next": "right",
        },
        "selectors": {
            "prev_button": 'button[aria-keyshortcuts*=PageUp]:not([aria-disabled=true])', # 'button[aria-label="Previous page"]',
            "next_button": 'button[aria-keyshortcuts*=PageDown]:not([aria-disabled=true])', # 'button[aria-label="Next page"]',
            "screenshot": 'main > div > div > div > div > div > div',
            "pagination": 'div[role="navigation"] button:has(p)'
        },
        "hide": ["header", "footer"]  
    }]
}

# Parameters
DEFAULT_MAX_PAGES = None  # None pour toutes les pages
DEFAULT_OUTPUT = "slides-images.pdf"
DEFAULT_URL = ""

# Selectors
DEFAULT_SELECTORS = {
    "prev_button": 'button[aria-keyshortcuts*=PageUp]',
    "next_button": 'button[aria-keyshortcuts*=PageDown]',
    "title": 'title',
    "pagination": '[role="navigation"]'
}