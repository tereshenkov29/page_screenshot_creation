import os
import re
import codecs
import shutil
from datetime import datetime
import requests
# --- ИЗМЕНЕНИЕ: Импортируем 'Page' для подсказок типов, убираем 'sync_playwright' ---
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from pdf2image import convert_from_path


#
# --- ИЗМЕНЕНИЕ: Функция теперь принимает объект 'page' и больше не управляет браузером ---
#
def take_screenshot(
        page: Page,  # <--- ГЛАВНОЕ ИЗМЕНЕНИЕ
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
    """Обрабатывает URL веб-страницы на УЖЕ ОТКРЫТОЙ вкладке браузера."""
    if not (full_page or visible_only or save_mhtml):
        return []

    date_str = datetime.now().strftime("%Y-%m-%d")
    root_folder = os.path.join(base_folder, f"{date_str} - {site_name}")
    safe_url = sanitize_filename(url)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved_paths = []

    try:
        # --- ИЗМЕНЕНИЕ: Установка ширины viewport для текущей страницы ---
        original_viewport_size = page.viewport_size
        if use_1280_width:
            log_func("  📏 Устанавливаю ширину экрана 1280px")
            page.set_viewport_size({"width": 1280, "height": original_viewport_size['height']})
            page.wait_for_timeout(500)

        log_func(f"  Перехожу по URL: {url}")
        page.goto(url, timeout=45000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        if handle_cookie and cookie_button_text:
            log_func(f"  🍪 Ищу cookie-баннер с текстом '{cookie_button_text}'...")
            try:
                cookie_button = page.locator(
                    f"xpath=//*[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{cookie_button_text.lower()}')]").first
                cookie_button.wait_for(timeout=7000)
                log_func("  ✅ Баннер найден, кликаю...")
                cookie_button.click(force=True)
                page.wait_for_timeout(1500)
                log_func("  👍 Баннер успешно закрыт.")
            except PlaywrightTimeoutError:
                log_func(f"  ⚠️ Не удалось найти видимую кнопку cookie-баннера за 7 секунд.")
            except Exception as e:
                log_func(f"  ❌ Произошла ошибка при обработке cookie-баннера: {e}")

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
                log_func("  📜 Прокручиваю страницу для загрузки всего контента...")
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
            # --- ИЗМЕНЕНИЕ: Получаем CDP сессию из page.context ---
            cdp_session = page.context.new_cdp_session(page)
            mhtml_data = cdp_session.send("Page.captureSnapshot", {"format": "mhtml"})['data']
            cdp_session.detach()
            with codecs.open(mhtml_path, 'w', 'utf-8') as f:
                f.write(mhtml_data)
            saved_paths.append(mhtml_path)

    except PlaywrightTimeoutError:
        log_func(f"❌ Ошибка: страница {url} не загрузилась за 45 секунд.")
    except Exception as e:
        log_func(f"❌ Ошибка при обработке {url}: {e}")
    finally:
        # --- ИЗМЕНЕНИЕ: Возвращаем viewport к исходному размеру, если он менялся ---
        if use_1280_width and page.viewport_size != original_viewport_size:
            page.set_viewport_size(original_viewport_size)
        # БРАУЗЕР ЗДЕСЬ НЕ ЗАКРЫВАЕМ!

    return saved_paths


#
# --- ФУНКЦИЯ ОБРАБОТКИ PDF ОСТАЕТСЯ БЕЗ ИЗМЕНЕНИЙ ---
#
def process_pdf(
        url: str,
        base_folder: str,
        site_name: str,
        take_visible_screenshot: bool = False,
        save_as_is: bool = False,
        log_func=print
) -> list[str]:
    """Надежно обрабатывает URL PDF: скачивает, сохраняет и/или конвертирует в изображение."""
    # ... (весь код этой функции остается прежним) ...
    if not (take_visible_screenshot or save_as_is):
        return []

    date_str = datetime.now().strftime("%Y-%m-%d")
    root_folder = os.path.join(base_folder, f"{date_str} - {site_name}")
    saved_paths = []
    temp_pdf_path = None

    try:
        log_func(f"  📄 Загружаю PDF для обработки: {url}")
        response = requests.get(url, timeout=60, headers={'User-Agent': 'Mozilla/5.0'})
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
            log_func(f"  ✅ PDF-файл сохранен: {final_save_path}")

        if take_visible_screenshot:
            log_func(f"  🖼️ Конвертирую PDF в изображение с помощью Poppler...")

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
                log_func(f"  ✅ Скриншот PDF сохранен: {screenshot_path}")
            else:
                log_func(f"  ⚠️ Не удалось создать изображение из PDF.")

    except requests.RequestException as e:
        log_func(f"  ❌ Не удалось скачать PDF из {url}. Ошибка: {e}")
    except Exception as e:
        log_func(f"  ❌ Ошибка при обработке PDF: {e}")
        if "Poppler" in str(e):
            log_func("  ... Убедитесь, что Poppler установлен и путь к нему в коде (poppler_path) указан верно.")
    finally:
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            try:
                shutil.rmtree(os.path.dirname(temp_pdf_path))
            except OSError as e:
                log_func(f"  ⚠️ Не удалось удалить временную папку: {e}")

    return saved_paths


# --- Вспомогательные функции (без изменений) ---

def auto_scroll(page):
    """Плавно прокручивает страницу до самого низа."""
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
    """Очищает URL или имя файла для использования в качестве имени файла."""
    if "://" in url_or_filename:
        clean_name = re.sub(r'^https?://', '', url_or_filename)
    else:
        clean_name = url_or_filename

    clean_name = re.sub(r'^www\.', '', clean_name)
    clean_name = re.sub(r'[\\/*?:"<>|]', '_', clean_name)
    if clean_name.endswith('/'):
        clean_name = clean_name[:-1]
    return clean_name[:100]

