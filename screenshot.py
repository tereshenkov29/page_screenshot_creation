import os
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from webdriver_manager.chrome import ChromeDriverManager


def wait_for_all_images(driver, timeout=15):
    """Ждёт, пока все <img> на странице будут загружены."""
    WebDriverWait(driver, timeout).until(lambda d: d.execute_script("""
        return Array.from(document.images).every(img => img.complete && img.naturalHeight > 0);
    """))


def take_fullpage_screenshot(url: str) -> str:
    output_dir = "screenshots"
    os.makedirs(output_dir, exist_ok=True)

    safe_url = url.replace("https://", "").replace("http://", "").replace("/", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{safe_url}_{timestamp}.png"
    filepath = os.path.join(output_dir, filename)

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        driver.get(url)

        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        try:
            wait_for_all_images(driver)
        except TimeoutException:
            print("⚠️ Не все изображения успели загрузиться за отведённое время.")

        # Получаем реальные размеры
        width = driver.execute_script("return document.body.scrollWidth")
        height = driver.execute_script("return document.body.scrollHeight")
        driver.set_window_size(width, height)
        time.sleep(1)

        driver.save_screenshot(filepath)
        print(f"✅ Скриншот сохранён: {filepath}")
        return filepath
    finally:
        driver.quit()


if __name__ == "__main__":
    take_fullpage_screenshot("https://properaccess.nl/")