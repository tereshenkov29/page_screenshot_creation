from flask import Flask, request, render_template_string, jsonify, redirect
from screenshot_playwright import take_fullpage_screenshot
from upload_to_shared_drive import upload_all_screenshots_to_shared_drive
import threading
import time
import os

app = Flask(__name__)

# Глобальные переменные для логов и результата
log_lines = []
folder_link = None
task_running = False

HTML_FORM = """
<!doctype html>
<title>Скриншотер</title>
<h1>Создание скриншотов</h1>
<form method=post action="/">
  <textarea name=urls rows=10 cols=80 placeholder="Вставьте по одной ссылке на строку"></textarea><br><br>
  <input type=submit value="Сделать скриншоты">
</form>
"""

HTML_STATUS = """
<!doctype html>
<title>Прогресс выполнения</title>
<h1>📸 Выполнение задачи</h1>
<pre id="log" style="border: 1px solid #ccc; padding: 10px; background: #f9f9f9;">{{ log }}</pre>
{% if folder_link %}
  <h2>✅ Готово</h2>
  <p><a href="{{ folder_link | safe }}" target="_blank">Открыть папку в Google Drive</a></p>
{% else %}
  <p>⏳ Задача выполняется... страница обновляется каждые 2 сек</p>
  <script>
    setTimeout(() => {
      window.location.reload();
    }, 2000);
  </script>
{% endif %}
"""

def log(msg):
    print(msg)
    log_lines.append(msg)


@app.route("/", methods=["GET", "POST"])
def index():
    global log_lines, folder_link, task_running

    if request.method == "POST":
        if task_running:
            return "⛔ Уже выполняется задача. Попробуйте позже.", 429

        urls_text = request.form.get("urls", "")
        urls = [url.strip() for url in urls_text.splitlines() if url.strip()]
        log_lines = []
        folder_link = None
        task_running = True

        def worker():
            global folder_link, task_running
            try:
                successful_screens = []

                for url in urls:
                    log(f"🌐 Открываю: {url}")
                    result = take_fullpage_screenshot(url)
                    if result:
                        log(f"✅ Скриншот готов: {url}")
                        successful_screens.append(result)
                    else:
                        log(f"⚠️ Пропущено (не удалось загрузить): {url}")

                if successful_screens:
                    log("🚀 Начинаю загрузку в Shared Drive")
                    folder_link = upload_all_screenshots_to_shared_drive()
                    log(f"📁 Скриншоты загружены: {folder_link}")
                else:
                    log("⚠️ Ни один скриншот не был создан. Загрузка в Drive не выполнена.")

            except Exception as e:
                log(f"❌ Ошибка: {e}")
            finally:
                task_running = False
                log("🎉 Задача завершена.")

        threading.Thread(target=worker).start()
        return redirect("/status")  # <--- вот здесь теперь redirect!

    return render_template_string(HTML_FORM)


@app.route("/status")
def status():
    return render_template_string(HTML_STATUS, log="\n".join(log_lines), folder_link=folder_link)


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))