from concurrent.futures import ProcessPoolExecutor, as_completed
from screenshot_playwright import take_fullpage_screenshot

URLS = [
    "https://properaccess.nl/",
    "https://properaccess.nl/toegankelijkheidsaudit/",
    "https://properaccess.nl/cases/",
    "https://properaccess.nl/onderzoeksbureau-digitale-toegankelijkheid/",
    "https://properaccess.nl/blog_digitale_toegankelijkheid/",
    "https://properaccess.nl/community/",
    # можно добавлять дальше
]

def run_batch_screenshots(urls, max_workers=3):
    print(f"📸 Начинаю обработку {len(urls)} URL с {max_workers} параллельными процессами...")

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(take_fullpage_screenshot, url): url for url in urls}

        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                result_path = future.result()
                print(f"✅ Скриншот для {url} сохранён: {result_path}")
            except Exception as e:
                print(f"❌ Ошибка при обработке {url}: {e}")

if __name__ == "__main__":
    run_batch_screenshots(URLS)