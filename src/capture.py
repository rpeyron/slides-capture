
import base64
import hashlib
import io
import os
import re
import time

from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import urllib

from src.config import DEFAULT_OUTPUT, DEFAULT_SELECTORS, DEFAULT_URL, KEY_NAMES, CaptureConfig
from src.helpers import clean_text, sanitize_text


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

    final_output = os.path.join(config["output_path"], final_output)

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

