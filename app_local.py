from flask import Flask, request, jsonify, send_file
from screenshot_playwright import take_screenshot
from upload_to_shared_drive import upload_all_screenshots_to_shared_drive
from flask_cors import CORS
from zipfile import ZipFile
import threading
import os
import io
import datetime

app = Flask(__name__)
CORS(app)

# Глобальное состояние
log_lines = []
task_running = False
folder_link = None


def log(msg):
    print(msg)
    log_lines.append(msg)


@app.route("/create", methods=["POST"])
def create():
    global log_lines, folder_link, task_running

    if task_running:
        return jsonify({"error": "⛔ Уже выполняется задача"}), 429

    data = request.get_json()
    site_name = data.get("site", "site")
    urls_text = data.get("urls", "")
    full_page = data.get("full_page", False)
    visible_page = data.get("visible_page", False)

    urls = [url.strip() for url in urls_text.splitlines() if url.strip()]
    if not urls or not (full_page or visible_page):
        return jsonify({"error": "Некорректные данные"}), 400

    log_lines = []
    folder_link = None
    task_running = True

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
    root_dir = f"screenshots/{timestamp} - {site_name}"
    os.makedirs(root_dir, exist_ok=True)

    def worker():
        global folder_link, task_running
        try:
            successful = []

            for url in urls:
                log(f"🌐 Открываю: {url}")

                result_paths = take_screenshot(
                    url=url,
                    base_folder="screenshots",
                    site_name=site_name,
                    full_page=full_page,
                    visible_only=visible_page
                )

                for path in result_paths:
                    log(f"✅ Сохранено: {path}")
                    successful.append(path)

            if successful:
                log("🚀 Загружаю в Shared Drive")
                folder_link_url = upload_all_screenshots_to_shared_drive(root_dir)
                log(f"📁 Загружено: {folder_link_url}")
                globals()["folder_link"] = folder_link_url
            else:
                log("⚠️ Скриншоты не созданы")

        except Exception as e:
            log(f"❌ Ошибка: {e}")
        finally:
            task_running = False
            log("🎉 Задача завершена")

    threading.Thread(target=worker).start()
    return jsonify({"status": "started"})


@app.route("/status")
def status():
    return jsonify({
        "log": log_lines,
        "done": not task_running,
        "folder_link": folder_link
    })


@app.route("/download")
def download_zip():
    memory_file = io.BytesIO()
    with ZipFile(memory_file, 'w') as zf:
        for root, _, files in os.walk("screenshots"):
            for filename in files:
                if filename.endswith(".png"):
                    filepath = os.path.join(root, filename)
                    arcname = os.path.relpath(filepath, start="screenshots")
                    zf.write(filepath, arcname=arcname)
    memory_file.seek(0)
    return send_file(memory_file, download_name="screenshots.zip", as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
