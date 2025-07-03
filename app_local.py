from flask import Flask, request, jsonify, send_file
# --- ИЗМЕНЕНИЕ: Импортируем новые функции для обработки PDF и MHTML ---
from screenshot_playwright import take_screenshot, process_pdf
from upload_to_shared_drive import upload_all_screenshots_to_shared_drive
from flask_cors import CORS
from zipfile import ZipFile
import threading
import os
import io
import datetime
import logging

# --- УЛУЧШЕНИЕ: Настройка логирования ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
CORS(app)


# --- УЛУЧШЕНИЕ: Инкапсуляция состояния задачи для лучшей управляемости ---
class TaskState:
    def __init__(self):
        self.log_lines = []
        self.is_running = False
        self.folder_link = None

    def reset(self):
        self.log_lines = []
        self.is_running = False
        self.folder_link = None

    def log(self, msg):
        logging.info(msg)
        # Ограничиваем размер лога, чтобы избежать переполнения памяти
        if len(self.log_lines) > 200:
            self.log_lines.pop(0)
        self.log_lines.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")


# Глобальный объект состояния
task_state = TaskState()


@app.route("/create", methods=["POST"])
def create():
    """Эндпоинт для запуска задачи по созданию скриншотов и обработке PDF."""
    if task_state.is_running:
        return jsonify({"error": "⛔ Задача уже выполняется. Пожалуйста, подождите."}), 429

    data = request.get_json()
    if not data:
        return jsonify({"error": "Пустой запрос"}), 400

    task_state.reset()
    task_state.is_running = True
    task_state.log("🚀 Задача принята в работу...")

    # --- ИЗМЕНЕНИЕ: Получаем все параметры из нового фронтенда ---
    site_name = data.get("site", "site")
    urls_text = data.get("urls", "")
    pdf_urls_text = data.get("pdf_urls", "")

    # Опции для веб-страниц
    visible_page = data.get("visible_page", False)
    full_page = data.get("full_page", False)
    save_mhtml = data.get("save_mhtml", False)
    # --- НОВЫЙ ПАРАМЕТР: Получаем опцию ширины ---
    use_1280_width = data.get("use_1280_width", False)

    # Опции для PDF
    save_pdf = data.get("save_pdf", False)

    # Опции Cookie
    handle_cookie = data.get("handle_cookie", False)
    cookie_button_text = data.get("cookie_button_text", "")

    urls = [url.strip() for url in urls_text.splitlines() if url.strip()]
    pdf_urls = [url.strip() for url in pdf_urls_text.splitlines() if url.strip()]

    if not (urls or pdf_urls):
        task_state.is_running = False
        return jsonify({"error": "Не указана ни одна ссылка."}), 400
    if not (visible_page or full_page or save_mhtml or save_pdf):
        task_state.is_running = False
        return jsonify({"error": "Не выбрана ни одна опция обработки."}), 400

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
    root_dir = f"screenshots/{timestamp} - {site_name}"
    os.makedirs(root_dir, exist_ok=True)

    def worker():
        """Фоновый воркер для выполнения длительных задач."""
        try:
            successful_paths = []

            if urls:
                task_state.log(f"--- Обработка {len(urls)} веб-страниц ---")
                for url in urls:
                    try:
                        # --- НОВЫЙ ПАРАМЕТР: Передаем опцию ширины в функцию ---
                        result_paths = take_screenshot(
                            url=url,
                            base_folder="screenshots",
                            site_name=site_name,
                            full_page=full_page,
                            visible_only=visible_page,
                            save_mhtml=save_mhtml,
                            use_1280_width=use_1280_width,
                            handle_cookie=handle_cookie,
                            cookie_button_text=cookie_button_text,
                            log_func=task_state.log
                        )
                        successful_paths.extend(result_paths)
                    except Exception as e:
                        task_state.log(f"❌ Ошибка при обработке страницы {url}: {e}")

            if pdf_urls:
                task_state.log(f"--- Обработка {len(pdf_urls)} PDF-файлов ---")
                for url in pdf_urls:
                    try:
                        result_paths = process_pdf(
                            url=url,
                            base_folder="screenshots",
                            site_name=site_name,
                            take_visible_screenshot=visible_page,
                            save_as_is=save_pdf,
                            log_func=task_state.log
                        )
                        successful_paths.extend(result_paths)
                    except Exception as e:
                        task_state.log(f"❌ Ошибка при обработке PDF {url}: {e}")

            if successful_paths:
                task_state.log("☁️ Загружаю файлы в Shared Drive...")
                try:
                    folder_link_url = upload_all_screenshots_to_shared_drive(root_dir)
                    if folder_link_url:
                        task_state.log(f"📁 Ссылка на папку: {folder_link_url}")
                        task_state.folder_link = folder_link_url
                    else:
                        task_state.log("⚠️ Не удалось получить ссылку на папку после загрузки.")
                except Exception as upload_e:
                    task_state.log(f"❌ Ошибка при загрузке на Google Drive: {upload_e}")
            else:
                task_state.log("⚠️ Ни одного файла не было создано. Проверьте ссылки и настройки.")

        except Exception as e:
            task_state.log(f"❌ Критическая ошибка в задаче: {e}")
        finally:
            task_state.is_running = False
            task_state.log("🎉 Задача завершена.")

    threading.Thread(target=worker).start()
    return jsonify({"status": "started"})


@app.route("/status")
def status():
    """Эндпоинт для получения текущего статуса задачи."""
    return jsonify({
        "log": task_state.log_lines,
        "done": not task_state.is_running,
        "folder_link": task_state.folder_link
    })


@app.route("/download")
def download_zip():
    """Эндпоинт для скачивания всех созданных файлов в виде zip-архива."""
    screenshots_dir = "screenshots"
    if not os.path.exists(screenshots_dir) or not os.listdir(screenshots_dir):
        return "Нет файлов для скачивания.", 404

    memory_file = io.BytesIO()
    with ZipFile(memory_file, 'w') as zf:
        for root, _, files in os.walk(screenshots_dir):
            for filename in files:
                if filename.endswith((".png", ".mhtml", ".pdf")):
                    filepath = os.path.join(root, filename)
                    arcname = os.path.relpath(filepath, start=screenshots_dir)
                    zf.write(filepath, arcname=arcname)
    memory_file.seek(0)
    return send_file(memory_file, download_name="screenshots_and_files.zip", as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
