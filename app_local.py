from flask import Flask, request, jsonify, send_file
from screenshot_playwright import take_fullpage_screenshot
from upload_to_shared_drive import upload_all_screenshots_to_shared_drive
from flask_cors import CORS
from zipfile import ZipFile
import threading
import os
import io

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
    urls_text = data.get("urls", "")
    urls = [url.strip() for url in urls_text.splitlines() if url.strip()]

    if not urls:
        return jsonify({"error": "Список ссылок пуст"}), 400

    log_lines = []
    folder_link = None
    task_running = True

    def worker():
        global folder_link, task_running
        try:
            successful = []

            for url in urls:
                log(f"🌐 Открываю: {url}")
                result = take_fullpage_screenshot(url)
                if result:
                    log(f"✅ Скриншот готов: {url}")
                    successful.append(result)
                else:
                    log(f"⚠️ Пропущено: {url}")

            if successful:
                log("🚀 Загружаю в Shared Drive")
                folder_link_url = upload_all_screenshots_to_shared_drive()
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
        for filename in os.listdir("screenshots"):
            if filename.endswith(".png"):
                filepath = os.path.join("screenshots", filename)
                zf.write(filepath, arcname=filename)
    memory_file.seek(0)
    return send_file(memory_file, download_name="screenshots.zip", as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
