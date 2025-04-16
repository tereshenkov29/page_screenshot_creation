import os
from datetime import datetime
from playwright.sync_api import sync_playwright


def take_fullpage_screenshot(url: str) -> str:
    output_dir = "screenshots"
    os.makedirs(output_dir, exist_ok=True)

    # Формируем имя файла
    safe_url = url.replace("https://", "").replace("http://", "").replace("/", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{safe_url}_{timestamp}.png"
    filepath = os.path.join(output_dir, filename)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="nl"
        )
        page = context.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=120_000)
        except Exception as e:
            print(f"❌ Не удалось загрузить {url}: {e}")
            return None

        auto_scroll(page)
        page.wait_for_timeout(2000)

        # Скриншот всей страницы
        page.screenshot(path=filepath, full_page=True)

        print(f"✅ Скриншот сохранён: {filepath}")
        browser.close()

    return filepath

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

# Пример запуска
if __name__ == "__main__":
    take_fullpage_screenshot("https://properaccess.nl/")