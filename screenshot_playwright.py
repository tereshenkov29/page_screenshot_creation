import os
import re
import codecs
import shutil
from datetime import datetime
import requests
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from pdf2image import convert_from_path


def take_screenshot(
        page: Page,
        url: str,
        base_folder: str,
        site_name: str,
        full_page: bool = False,
        visible_only: bool = False,
        save_mhtml: bool = False,
        use_1280_width: bool = False,
        handle_cookie: bool = False,
        cookie_button_text: str = "",
        log_func=print
) -> list[str]:
    """Processes a web page URL on an ALREADY OPEN browser page."""
    if not (full_page or visible_only or save_mhtml):
        return []

    date_str = datetime.now().strftime("%Y-%m-%d")
    root_folder = os.path.join(base_folder, f"{date_str} - {site_name}")
    safe_url = sanitize_filename(url)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved_paths = []

    try:
        original_viewport_size = page.viewport_size
        if use_1280_width:
            log_func("  📏 Setting viewport width to 1280px")
            page.set_viewport_size({"width": 1280, "height": original_viewport_size['height']})
            page.wait_for_timeout(500)

        log_func(f"  Navigating to URL: {url}")
        page.goto(url, timeout=45000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        if handle_cookie and cookie_button_text:
            log_func(f"  🍪 Searching for cookie banner with text '{cookie_button_text}'...")
            try:
                # --- FINAL CHANGE: Update regex to ignore leading/trailing whitespace ---
                # The \s* allows for any number of whitespace characters before and after the text,
                # which is a common reason for locator failure.

                # Define the more robust regex
                text_regex = re.compile(f"^\s*{re.escape(cookie_button_text)}\s*$", re.IGNORECASE)

                # Define the two locators we want to try
                button_locator = page.get_by_role("button", name=text_regex)
                text_locator = page.get_by_text(text_regex)

                # Combine them with .or_() and find the first visible one
                combined_locator = button_locator.or_(text_locator).first

                # Wait for the element to be visible and click it
                combined_locator.wait_for(timeout=7000)
                log_func("  ✅ Banner element found, clicking...")
                combined_locator.click(force=True)
                page.wait_for_timeout(1500)
                log_func("  👍 Banner closed successfully.")
                # --- END CHANGE ---

            except PlaywrightTimeoutError:
                log_func(f"  ⚠️ Could not find a visible cookie banner element within 7 seconds.")
            except Exception as e:
                log_func(f"  ❌ An error occurred while handling the cookie banner: {e}")

        scrolled = False
        if visible_only:
            folder_suffix = "_1280px" if use_1280_width else ""
            visible_dir = os.path.join(root_folder, f"visible_page_screenshots{folder_suffix}")
            os.makedirs(visible_dir, exist_ok=True)
            visible_path = os.path.join(visible_dir, f"{timestamp}_{safe_url}.png")
            page.screenshot(path=visible_path, full_page=False)
            saved_paths.append(visible_path)

        if full_page or save_mhtml:
            if not scrolled:
                log_func("  📜 Scrolling the page to load all content...")
                auto_scroll(page)
                page.wait_for_timeout(1000)
                scrolled = True

        if full_page:
            folder_suffix = "_1280px" if use_1280_width else ""
            full_dir = os.path.join(root_folder, f"full_page_screenshots{folder_suffix}")
            os.makedirs(full_dir, exist_ok=True)
            full_path = os.path.join(full_dir, f"{timestamp}_{safe_url}.png")
            page.screenshot(path=full_path, full_page=True)
            saved_paths.append(full_path)

        if save_mhtml:
            mhtml_dir = os.path.join(root_folder, "mhtml_pages")
            os.makedirs(mhtml_dir, exist_ok=True)
            mhtml_path = os.path.join(mhtml_dir, f"{timestamp}_{safe_url}.mhtml")
            cdp_session = page.context.new_cdp_session(page)
            mhtml_data = cdp_session.send("Page.captureSnapshot", {"format": "mhtml"})['data']
            cdp_session.detach()
            with codecs.open(mhtml_path, 'w', 'utf-8') as f:
                f.write(mhtml_data)
            saved_paths.append(mhtml_path)

    except PlaywrightTimeoutError:
        log_func(f"❌ Error: Page {url} timed out after 45 seconds.")
    except Exception as e:
        log_func(f"❌ Error processing {url}: {e}")
    finally:
        if use_1280_width and page.viewport_size != original_viewport_size:
            page.set_viewport_size(original_viewport_size)

    return saved_paths


def process_pdf(
        url: str,
        base_folder: str,
        site_name: str,
        take_visible_screenshot: bool = False,
        save_as_is: bool = False,
        log_func=print
) -> list[str]:
    """Reliably processes a PDF URL: downloads, saves, and/or converts to an image."""
    if not (take_visible_screenshot or save_as_is):
        return []

    date_str = datetime.now().strftime("%Y-%m-%d")
    root_folder = os.path.join(base_folder, f"{date_str} - {site_name}")
    saved_paths = []
    temp_pdf_path = None

    try:
        log_func(f"  📄 Downloading PDF for processing: {url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'DNT': '1'
        }
        response = requests.get(url, timeout=60, headers=headers)

        response.raise_for_status()

        try:
            content_disp = response.headers.get('content-disposition')
            filename = re.findall('filename="?(.+)"?', content_disp)[0]
        except (TypeError, IndexError):
            filename = url.split('/')[-1].split('?')[0]

        safe_filename = sanitize_filename(filename)
        if not safe_filename.lower().endswith('.pdf'):
            safe_filename += '.pdf'

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_filename = f"{timestamp}_{safe_filename}"

        temp_dir = os.path.join(root_folder, "temp_pdf")
        os.makedirs(temp_dir, exist_ok=True)
        temp_pdf_path = os.path.join(temp_dir, final_filename)

        with open(temp_pdf_path, 'wb') as f:
            f.write(response.content)

        if save_as_is:
            pdf_dir = os.path.join(root_folder, "pdf_files")
            os.makedirs(pdf_dir, exist_ok=True)
            final_save_path = os.path.join(pdf_dir, final_filename)
            shutil.copy2(temp_pdf_path, final_save_path)
            saved_paths.append(final_save_path)
            log_func(f"  ✅ PDF file saved: {final_save_path}")

        if take_visible_screenshot:
            log_func(f"  🖼️ Converting PDF to image using Poppler...")

            poppler_path = r"C:\Users\Yakov\Downloads\Release-24.08.0-0\poppler-24.08.0\Library\bin"

            images = convert_from_path(
                temp_pdf_path,
                dpi=200,
                first_page=1,
                last_page=1,
                poppler_path=poppler_path
            )

            if images:
                pdf_screenshot_dir = os.path.join(root_folder, "pdf_screenshots")
                os.makedirs(pdf_screenshot_dir, exist_ok=True)
                screenshot_path = os.path.join(pdf_screenshot_dir, final_filename.replace('.pdf', '.png'))
                images[0].save(screenshot_path, 'PNG')
                saved_paths.append(screenshot_path)
                log_func(f"  ✅ PDF screenshot saved: {screenshot_path}")
            else:
                log_func(f"  ⚠️ Failed to create image from PDF.")

    except requests.RequestException as e:
        log_func(f"  ❌ Failed to download PDF from {url}. Error: {e}")
    except Exception as e:
        log_func(f"  ❌ Error processing PDF: {e}")
        if "Poppler" in str(e):
            log_func("  ... Ensure Poppler is installed and the 'poppler_path' in the code is correct.")
    finally:
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            try:
                shutil.rmtree(os.path.dirname(temp_pdf_path))
            except OSError as e:
                log_func(f"  ⚠️ Failed to delete temp folder: {e}")

    return saved_paths


def auto_scroll(page):
    """Smoothly scrolls the page to the very bottom."""
    page.evaluate("""
        async () => {
            await new Promise((resolve) => {
                let totalHeight = 0;
                const distance = 100;
                const timer = setInterval(() => {
                    const scrollHeight = document.body.scrollHeight;
                    window.scrollBy(0, distance);
                    totalHeight += distance;
                    if (totalHeight >= scrollHeight) {
                        clearInterval(timer);
                        resolve();
                    }
                }, 100);
            });
        }
    """)


def sanitize_filename(url_or_filename: str) -> str:
    """Cleans a URL or filename for use as a valid filename."""
    if "://" in url_or_filename:
        clean_name = re.sub(r'^https?://', '', url_or_filename)
    else:
        clean_name = url_or_filename

    clean_name = re.sub(r'^www\.', '', clean_name)
    clean_name = re.sub(r'[\\/*?:"<>|]', '_', clean_name)
    if clean_name.endswith('/'):
        clean_name = clean_name[:-1]
    return clean_name[:100]

