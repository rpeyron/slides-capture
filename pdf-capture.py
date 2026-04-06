import os
import urllib.request
import re
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from PIL import Image
import io
import time
import hashlib
import base64
import unicodedata
import json

from typing import TypedDict, NotRequired, Literal

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



# Default Config
DEFAULT_CONFIG : CaptureConfig= {
    "config": "config.json",
    # Delay after clicking next/prev button (default: 0.5s)
    "delay_after_click": 2,
    # Maximum number of pages to capture (None for all)
    "max_pages": None, 
    # Output path
    "output_path": "out",
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


def sanitize_text(text):
    normalized = unicodedata.normalize('NFKD', text or '')
    ascii_text = normalized.encode('ascii', 'ignore').decode('ascii')
    clean = re.sub(r"[^A-Za-z0-9 ._\-]", " ", ascii_text)
    return re.sub(r"\s+", " ", clean).strip()


def clean_text(text):
    return re.sub(r"\s+", " ", (text or "")).strip()

def config_site_for_url(config: CaptureConfig, url: str):
    def_site = {"name": "Default Slideshow", "url_pattern": "", "selectors": DEFAULT_SELECTORS}
    for site in config.get("sites", []):
        if site.get("url_pattern"):
            if re.match(site["url_pattern"], url):
                return site
        elif site.get("url_contains"):
            if site["url_contains"] in url:
                return site
        else:
            def_site = site
    return def_site

def screenshot_thumbnail(screenshot_path, thumb_path):
    try:
        img = Image.open(screenshot_path)
        img.thumbnail((400, 300))
        img.save(thumb_path)
        with open(thumb_path, 'rb') as f:
            data = f.read()
        return 'data:image/png;base64,' + base64.b64encode(data).decode()
    except Exception:
        return None


def get_pagination_info(driver, config_site):
    selector = config_site.get("selectors", {}).get("pagination")
    try:
        raw_pagination = driver.find_element(By.CSS_SELECTOR, selector).text
        pagination = clean_text(raw_pagination)
        numbers = re.findall(r'\d+', pagination)
        if len(numbers) >= 2:
            current = int(numbers[0])
            total = int(numbers[-1])
            return pagination, current, total
        return pagination, None, None
    except Exception:
        return None, None, None

def hide_elements(driver, selectors):
    if selectors:
        for selector in selectors:
            try:
                elements_to_hide = driver.find_elements(By.CSS_SELECTOR, selector)
                for el in elements_to_hide:
                    driver.execute_script("arguments[0].style.visibility='hidden'", el)
                    #driver.execute_script("arguments[0].style.display='none'", el)
            except Exception:
                pass
        time.sleep(0.5)

def show_elements(driver, selectors):
    if selectors:
        for selector in selectors:
            try:
                elements_to_show = driver.find_elements(By.CSS_SELECTOR, selector)
                for el in elements_to_show:
                    driver.execute_script("arguments[0].style.visibility=''", el)
                    #driver.execute_script("arguments[0].style.display='block'", el)
            except Exception:
                pass
        time.sleep(0.5)

def capture_pages_to_pdf(config: CaptureConfig, progress_dict=None, download_hashes_dict=None):
    
    progress = progress_dict
    download_hashes = download_hashes_dict
    
    url = config.get("url", DEFAULT_URL)
    output_pdf = config.get("output")
    max_pages = config.get("max_pages")
    headless = config.get("engine", {}).get("headless", False)
    output_path = config.get("output_path", "out")
    selenium_url = config.get("engine", {}).get("selenium_url", None)

    screenshot_path = os.path.join(output_path, 'screenshot.png')
    thumb_path = os.path.join(output_path, 'screenshot_thumb.png')

    config_site = config_site_for_url(config, url)
    print(f"Using site configuration: {config_site['name']}")

    config_site_selectors = config_site.get("selectors", {})
    PREV_BUTTON_SELECTOR = config_site_selectors.get("prev_button", DEFAULT_SELECTORS["prev_button"])
    NEXT_BUTTON_SELECTOR = config_site_selectors.get("next_button", DEFAULT_SELECTORS["next_button"])
    TITLE_SELECTOR = config_site_selectors.get("title", DEFAULT_SELECTORS["title"])
    PAGINATION_SELECTOR = config_site_selectors.get("pagination", DEFAULT_SELECTORS["pagination"])

    IMAGE_SELECTOR = config_site_selectors.get("image", None)
    SCREENSHOT_SELECTOR = config_site_selectors.get("screenshot", None)

    if url is None:
        url = DEFAULT_URL

    os.makedirs(output_path, exist_ok=True)

    thumb_path = f"{output_path}/screenshot_thumb.png"
    if os.path.exists(thumb_path):
        os.remove(thumb_path)

    # Options Chrome
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    if selenium_url:
        print("Connecting to Selenium server at:", selenium_url)
        driver = webdriver.Remote(
            command_executor=selenium_url,
            options=chrome_options
        )
    else:
        print("Starting local ChromeDriver...")
        driver = webdriver.Chrome(options=chrome_options)

    driver.implicitly_wait(2)
    driver.get(url)
    time.sleep(1)

    if progress:
        progress['status'] = "Initialisation"
        driver.save_screenshot(screenshot_path)
        progress['screenshot_data'] = screenshot_thumbnail(screenshot_path, thumb_path)

    images = []
    seen_urls = set()

    # 1. Aller au début (previous tant que possible)
    while True:
        try:
            if config_site.get("keys", {}).get("prev"):
                prevpage = get_pagination_info(driver, config_site)[0]
                driver.find_element(By.TAG_NAME, 'body').send_keys(KEY_NAMES[config_site["keys"]["prev"]])  
                time.sleep(0.5)
                curpage = get_pagination_info(driver, config_site)[0]
                if curpage == prevpage:
                    break
            else:
                prev_btn = driver.find_element(By.CSS_SELECTOR, PREV_BUTTON_SELECTOR)
                prev_btn.click()
                time.sleep(0.5)
        except Exception:
            break

    # 2. Parcourir les pages
    i = 0
    while max_pages is None or i < max_pages:
        page_info = f"Screen {i + 1}"

        title = None

        # Titre du document
        if TITLE_SELECTOR:
            try:
                raw_title = driver.find_element(By.CSS_SELECTOR, TITLE_SELECTOR).text
                title = sanitize_text(raw_title)
            except Exception:
                pass

        if not title:
            try:
                raw_title = driver.title
                if raw_title:
                    title = sanitize_text(raw_title)
            except Exception:
                pass

        if title:
            if progress:
                progress['title'] = title


        # Pagination
        try:
            pagination, current, total = get_pagination_info(driver, config_site)
            if current is not None and total is not None and total > 0:
                try:
                    percent = (current / total) * 100
                    if progress:
                        progress['percent'] = percent
                except (ValueError, ZeroDivisionError):
                    pass
            page_info += f" | {pagination}"
        except Exception:
            pagination = None

        print(page_info)
        if progress:
            progress['status'] = page_info
            driver.save_screenshot(screenshot_path)
            progress['screenshot_data'] = screenshot_thumbnail(screenshot_path, thumb_path)

        # 2.1. Trouver toutes les images des slides
        if IMAGE_SELECTOR:
            img_elements = driver.find_elements(By.CSS_SELECTOR, IMAGE_SELECTOR)

            if not img_elements:
                print("No images found on this page, skipping.")
                # Continue to next page
            else:
                captured_for_page = []

                # 2.2. Traiter une image unique par URL
                for img_el in img_elements:
                    src = img_el.get_attribute("src")
                    if not src or not src.startswith('http'):
                        continue

                    if src in seen_urls:
                        continue

                    seen_urls.add(src)

                    try:
                        with urllib.request.urlopen(src) as response:
                            content = response.read()
                            img = Image.open(io.BytesIO(content))
                            #img = img.convert("RGB")
                            #img = img.resize((720, 960), Image.LANCZOS)
                            captured_for_page.append(img)
                    except Exception as e:
                        print("Failed to download image:", e)

                # 2.3. Ajouter les images capturées à la liste globale
                images.extend(captured_for_page)

        elif SCREENSHOT_SELECTOR:
            try:
                hide_elements(driver, config_site.get("hide", []))
                screenshot_el = driver.find_element(By.CSS_SELECTOR, SCREENSHOT_SELECTOR)
                screenshot_data = screenshot_el.screenshot_as_png
                img = Image.open(io.BytesIO(screenshot_data))
                #img = img.convert("RGB")
                #img = img.resize((720, 960), Image.LANCZOS)
                if images.__len__() > 0:
                    if (img.tobytes() == images[-1].tobytes()):
                        print("Same screenshot as previous, stop.")
                        break
                images.append(img)
                show_elements(driver, config_site.get("hide", []))
            except Exception as e:
                print("Failed to capture screenshot:", e)

        # 2.4. Passer à la page suivante
        if config_site.get("keys", {}).get("next"):
            prevpage = get_pagination_info(driver, config_site)[0]
            driver.find_element(By.TAG_NAME, 'body').send_keys(KEY_NAMES[config_site["keys"]["next"]])
            time.sleep(config.get("delay_after_click", 0.5))
            curpage = get_pagination_info(driver, config_site)[0]
            if prevpage and curpage and prevpage == curpage:
                print("Pagination stayed the same, no next page.")
                break
        else:
            try:
                next_btn = driver.find_element(By.CSS_SELECTOR, NEXT_BUTTON_SELECTOR)
                next_btn.click()
                time.sleep(config.get("delay_after_click", 0.5))
            except Exception:
                print("No next button. Stopping.")
                break

        i += 1

    # 3. Créer le PDF
    if not images:
        print("No images were captured.")
        driver.quit()
        return

    if output_pdf:
        final_output = output_pdf
    else:   
        if title:
            print(f"Document title: {title}")   
            final_output = f"{title}.pdf"
        else:  
            final_output = DEFAULT_OUTPUT

    final_output = os.path.join('out', final_output)

    print(f"Generating PDF with {len(images)} images...")

    images[0].save(
        final_output,
        "PDF",
        resolution=100.0,
        save_all=True,
        append_images=images[1:],
    )

    print(f"PDF saved as {final_output} (100.0%)")
    if progress:
        progress['file'] = final_output
        hash = hashlib.sha256(os.urandom(16)).hexdigest()[:16]
        if download_hashes is not None:
            download_hashes[hash] = os.path.basename(final_output)
        progress['download_hash'] = hash
        progress['percent'] = 100.0
        progress['status'] = "Terminé"
    driver.quit()


if __name__ == "__main__":
    import argparse

    config = DEFAULT_CONFIG
    DEFAULT_CONFIG_SITES = DEFAULT_CONFIG.get('sites', [])

    parser = argparse.ArgumentParser(description="Capture images from slideshow to PDF")
    parser.add_argument("-u", "--url", default=None, help="URL of the slideshow")
    parser.add_argument("-o", "--output", default=None, help="Output PDF file")
    parser.add_argument("-m", "--max-pages", type=int, default=DEFAULT_MAX_PAGES, help="Max pages to capture (default: all)")
    parser.add_argument("--headless", action="store_true", help="Run Chrome in headless mode")
    parser.add_argument("-c", "--config", default=config.get('config'), help="Path to JSON config file with site definitions and options")
    
    args = parser.parse_args()

    try:
        with open(args.config, 'r') as f:
            print(f"Loading config from {args.config}")
            user_config = json.load(f)
            config.update(user_config)
            # Re-Add default site definition
            config['sites'].extend(DEFAULT_CONFIG_SITES)
            print(f"Config loaded: {config}")
    except Exception as e:
        if args.config:
            print("Failed to load config file:", e)
            exit(1)
    
    if args.url:
        config['url'] = args.url
    if args.output:
        config['output'] = args.output
    if args.max_pages:
        config['max_pages'] = args.max_pages
    if args.headless:   
        config['engine']['headless'] = args.headless


    # If arguments provided, launch command line, else start web app
    if not (args.url is None and args.output is None and args.max_pages == DEFAULT_MAX_PAGES and not args.headless):
        capture_pages_to_pdf(config)

    else:
        # Web application definition
        from flask import Flask, request, jsonify, render_template_string
        import threading

        app = Flask(__name__)
        progress = {'percent': 0, 'status': '', 'file': None, 'screenshot_data': None}
        download_hashes = {}

        def run_script(config):
            progress['screenshot_data'] = None
            capture_pages_to_pdf(config, progress, download_hashes)

        @app.route('/')
        def index():
            return render_template_string('''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Capture Slides to PDF</title>
    <style>
        body { font-family: Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #333; margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; height: 100vh; }
        .container { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.1); max-width: 500px; width: 100%; }
        h1 { text-align: center; color: #4a5568; margin-bottom: 30px; }
        form { display: flex; flex-direction: column; }
        label { margin-bottom: 5px; font-weight: bold; color: #2d3748; }
        input[type="text"], input[type="number"] { padding: 10px; margin-bottom: 20px; border: 1px solid #e2e8f0; border-radius: 5px; font-size: 16px; width: 100%; box-sizing: border-box; }
        input[type="checkbox"] { margin-right: 10px; }
        .checkbox-label { display: flex; align-items: center; margin-bottom: 20px; }
        button { background: #667eea; color: white; padding: 12px; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; transition: background 0.3s; }
        button:hover { background: #5a67d8; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Capture Slides to PDF</h1>
        <form method="post" action="/process">
            <label for="url">URL du slideshow:</label>
            <input type="text" id="url" name="url" value="''' + DEFAULT_URL + '''" required>
            
            <details style="margin-top: 20px;">
                <summary style="cursor: pointer; margin-bottom: 20px; font-weight: bold; color: #667eea;">Options avancées</summary>
                <div style="padding-top: 10px; border-top: 1px solid #e2e8f0; margin-top: 10px;">
                    <div style="margin-bottom: 20px;">
                        <label for="output">Nom du fichier PDF (optionnel, utilise le titre si vide):</label>
                        <input type="text" id="output" name="output" placeholder="Laisser vide pour utiliser le titre">
                    </div>
                    
                    <div style="margin-bottom: 20px;">
                        <label for="max_pages">Nombre max de pages (optionnel):</label>
                        <input type="number" id="max_pages" name="max_pages" min="1">
                    </div>
                    
                    <div>
                        <label class="checkbox-label">
                            <input type="checkbox" name="headless">
                            Mode headless (sans interface)
                        </label>
                    </div>
                </div>
            </details>
            
            <button type="submit">Démarrer la capture</button>
        </form>
    </div>
</body>
</html>
''')
        
        @app.route('/process', methods=['POST'])
        def process():
            config['url'] = request.form['url']
            config['output'] = request.form['output'] if request.form['output'].strip() else None
            if config['output']:
                import os
                config['output'] = os.path.basename(config['output'])
                if not config['output'].endswith('.pdf'):
                    config['output'] += '.pdf'
            if request.form.get('max_pages'):
                config['max_pages'] = int(request.form.get('max_pages', 0))
            config['headless'] = 'headless' in request.form
            threading.Thread(target=run_script, args=([config])).start()
            return render_template_string('''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Traitement en cours</title>
    <style>
        body { font-family: Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #333; margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; height: 100vh; }
        .container { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.1); max-width: 600px; width: 100%; text-align: center; }
        h1 { color: #4a5568; margin-bottom: 30px; }
        #status { background: #f7fafc; padding: 15px; border-radius: 5px; margin-bottom: 20px; font-family: monospace; white-space: pre-wrap; min-height: 60px; display: flex; align-items: center; justify-content: center; }
        .progress-container { position: relative; width: 100%; height: 3em; background: #ddd; border-radius: 5px; overflow: hidden; }
        .progress-bar { height: 100%; background: green; position: relative; transition: width 0.3s; }
        .progress-bar.error { background: red; }
        .progress-label { position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 14px; }
        .download-btn { background: green; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Processing...</h1>
        <div id="title" style="margin-bottom: 10px; font-size: 18px; font-weight: bold;"></div>
        <div class="progress-container">
            <div class="progress-bar ok" id="progress-bar"></div>
            <div class="progress-label" id="progress-text">Initialization</div>
        </div>
        <div id="download-section" style="display: none; margin-top: 20px;">
            <a id="download-link" href="#" class="download-btn">Download PDF</a>
        </div>
        <img id="screenshot" style="display: block; margin: 20px auto; max-width: 100%; border: 1px solid #ccc;">
        <script>
            function update() {
                fetch('/progress').then(r => r.json()).then(data => {
                    if (data.title) {
                        document.getElementById('title').textContent = data.title;
                    }
                    document.getElementById('progress-bar').style.width = data.percent + '%';
                    document.getElementById('progress-bar').className = 'progress-bar ' + (data.status && (data.status.includes('Failed') || data.status.includes('Error')) ? 'error' : 'ok');
                    document.getElementById('progress-text').textContent = data.status || 'Initialisation';
                    if (data.file) {
                        document.getElementById('download-section').style.display = 'block';
                        document.getElementById('download-link').href = '/download/' + data.download_hash;
                        document.getElementById('screenshot').style.display = 'none';
                    }
                    if (data.screenshot_data) {
                        const img = document.getElementById('screenshot');
                        img.style.display = 'block';
                        img.src = data.screenshot_data;
                    }
                }).catch(err => console.error('Erreur de mise à jour:', err));
            }
            update();
            setInterval(update, 1000);
        </script>
    </div>
</body>
</html>
''')   

        @app.route('/progress')
        def get_progress():
            return jsonify(progress)

        @app.route('/download/<hash>')
        def download(hash):
            import os
            from flask import send_file
            if hash in download_hashes:
                filename = download_hashes[hash]
                return send_file(os.path.join('out', filename), as_attachment=True)
            return "File not found", 404

        app.run(host="0.0.0.0", port=5000,debug=True)

