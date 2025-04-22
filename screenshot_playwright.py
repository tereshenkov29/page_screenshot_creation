import os
import re
from datetime import datetime
from playwright.sync_api import sync_playwright


def take_screenshot(url: str, base_folder: str, site_name: str, full_page=False, visible_only=False) -> list[str]:
    if not (full_page or visible_only):
        return []

    date_str = datetime.now().strftime("%Y-%m-%d")
    root_folder = os.path.join(base_folder, f"{date_str} - {site_name}")
    safe_url = sanitize_filename(url)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved_paths = []

    with sync_playwright() as p:
        chromium_executable = p.chromium.executable_path
        browser = p.chromium.launch(headless=True, executable_path=chromium_executable)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="nl"
        )
        page = context.new_page()

        try:
            page.goto(url, timeout=30000)
            page.wait_for_timeout(2000)

            if visible_only:
                visible_dir = os.path.join(root_folder, "visible_page_screenshots")
                os.makedirs(visible_dir, exist_ok=True)
                visible_path = os.path.join(visible_dir, f"{timestamp}_{safe_url}.png")
                page.wait_for_timeout(500)
                page.screenshot(path=visible_path, full_page=False)
                print(f"✅ Скриншот видимой части сохранён: {visible_path}")
                saved_paths.append(visible_path)

            if full_page:
                auto_scroll(page)
                page.wait_for_timeout(1000)
                full_dir = os.path.join(root_folder, "full_page_screenshots")
                os.makedirs(full_dir, exist_ok=True)
                full_path = os.path.join(full_dir, f"{timestamp}_{safe_url}.png")
                page.screenshot(path=full_path, full_page=True)
                print(f"✅ Скриншот всей страницы сохранён: {full_path}")
                saved_paths.append(full_path)


        except Exception as e:
            print(f"❌ Ошибка при обработке {url}: {e}")

        finally:
            browser.close()

    return saved_paths


def auto_scroll(page):
    page.evaluate("""
        () => {
            return new Promise(resolve => {
                let totalHeight = 0;
                const distance = 100;
                const timer = setInterval(() => {
                    window.scrollBy(0, distance);
                    totalHeight += distance;
                    if (totalHeight >= document.body.scrollHeight) {
                        clearInterval(timer);
                        resolve();
                    }
                }, 100);
            });
        }
    """)


def sanitize_filename(url: str) -> str:
    clean_url = re.sub(r'^https?://', '', url)
    clean_url = re.sub(r'[\\/*?:"<>|]', '_', clean_url)
    return clean_url


# Пример ручного вызова
if __name__ == "__main__":
    take_screenshot(
        url="https://properaccess.nl/",
        base_folder="screenshots",
        site_name="properaccess.nl",
        full_page=True,
        visible_only=True
    )
