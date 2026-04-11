import threading

from src.argparse import parse_args
from src.config import DEFAULT_MAX_PAGES
from src.capture import capture_pages_to_pdf    
from src.tray import run_tray
from src.webapp import run_web_app

if __name__ == "__main__":
    args, config = parse_args()
    # If arguments provided, launch command line, else start web app
    if not (args.url is None and args.output is None and args.max_pages == DEFAULT_MAX_PAGES and not args.headless):
        capture_pages_to_pdf(config)
    else:
        def thread_web_app():
            run_web_app(config)
        flask_thread = threading.Thread(target=thread_web_app, daemon=True)
        flask_thread.start()
        run_tray(config)