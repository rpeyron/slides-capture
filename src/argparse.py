




import json
import sys

from src.config import DEFAULT_CONFIG, DEFAULT_CONFIG_FILE, DEFAULT_MAX_PAGES


def parse_args():
    import argparse

    config = DEFAULT_CONFIG
    DEFAULT_CONFIG_SITES = DEFAULT_CONFIG.get('sites', [])

    parser = argparse.ArgumentParser(description="Capture images from slideshow to PDF")
    parser.add_argument("-u", "--url", default=None, help="URL of the slideshow")
    parser.add_argument("-o", "--output", default=None, help="Output PDF file")
    parser.add_argument("-m", "--max-pages", type=int, default=DEFAULT_MAX_PAGES, help="Max pages to capture (default: all)")
    parser.add_argument("--headless", action="store_true", help="Run Chrome in headless mode")
    parser.add_argument("-c", "--config", default=None, help="Path to JSON config file with site definitions and options")
    
    args = parser.parse_args()
    configfile = args.config or config["config"] or DEFAULT_CONFIG_FILE
    
    try:
        with open(configfile, 'r') as f:
            print(f"Loading config from {configfile}")
            user_config = json.load(f)
            config.update(user_config)
            # Re-Add default site definition
            config['sites'].extend(DEFAULT_CONFIG_SITES)
            print(f"Config loaded: {config}")
    except Exception as e:
        if args.config:
            print("Failed to load config file:", e)
            sys.exit(1)
    
    if args.url:
        config['url'] = args.url
    if args.output:
        config['output'] = args.output
    if args.max_pages:
        config['max_pages'] = args.max_pages
    if args.headless:   
        config['engine']['headless'] = args.headless

    return (args, config)