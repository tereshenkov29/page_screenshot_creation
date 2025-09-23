from flask import Flask, request, jsonify, send_file
from playwright.sync_api import sync_playwright
# --- CHANGE: Import the new and renamed functions ---
from screenshot_playwright import _take_screenshot_on_page, take_screenshot_in_new_session, process_pdf
from upload_to_shared_drive import upload_all_screenshots_to_shared_drive
from flask_cors import CORS
from zipfile import ZipFile
import threading
import os
import io
import datetime
import logging
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
CORS(app)


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
        if len(self.log_lines) > 200:
            self.log_lines.pop(0)
        self.log_lines.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")


task_state = TaskState()


@app.route("/create", methods=["POST"])
def create():
    """Endpoint to start the screenshot and PDF processing task."""
    if task_state.is_running:
        return jsonify({"error": "⛔ A task is already running. Please wait."}), 429

    data = request.get_json()
    if not data:
        return jsonify({"error": "Empty request"}), 400

    task_state.reset()
    task_state.is_running = True
    task_state.log("🚀 Task accepted for processing...")

    site_name = data.get("site", "site")

    if site_name:
        site_name = re.sub(r'[\\/*?:"<>|]', '_', site_name)

    urls_text = data.get("urls", "")
    pdf_urls_text = data.get("pdf_urls", "")

    visible_page = data.get("visible_page", False)
    full_page = data.get("full_page", False)
    save_mhtml = data.get("save_mhtml", False)
    use_1280_width = data.get("use_1280_width", False)
    save_pdf = data.get("save_pdf", False)
    handle_cookie = data.get("handle_cookie", False)
    cookie_button_text = data.get("cookie_button_text", "")

    use_multi_session = data.get("use_multi_session", False)

    urls = [url.strip() for url in urls_text.splitlines() if url.strip()]
    pdf_urls = [url.strip() for url in pdf_urls_text.splitlines() if url.strip()]

    if not (urls or pdf_urls):
        task_state.is_running = False
        return jsonify({"error": "No URLs provided."}), 400
    if not (visible_page or full_page or save_mhtml or save_pdf):
        task_state.is_running = False
        return jsonify({"error": "No processing option selected."}), 400

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
    root_dir = f"screenshots/{timestamp} - {site_name}"
    os.makedirs(root_dir, exist_ok=True)

    def worker():
        """Background worker to perform long-running tasks."""
        try:
            successful_paths = []

            if urls:
                if use_multi_session:
                    task_state.log(f"--- Processing {len(urls)} web pages in MULTI-SESSION mode ---")
                    for i, url in enumerate(urls):
                        task_state.log(f"▶️  Processing URL ({i + 1}/{len(urls)}): {url}")
                        try:
                            result_paths = take_screenshot_in_new_session(
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
                            for path in result_paths:
                                task_state.log(f"  ✅ File saved: {os.path.basename(path)}")
                            successful_paths.extend(result_paths)
                        except Exception as e:
                            task_state.log(f"❌ Error processing page {url}: {e}")
                else:
                    task_state.log(f"--- Processing {len(urls)} web pages in SINGLE-SESSION mode ---")
                    task_state.log("🖥️  Launching browser for web page processing...")
                    with sync_playwright() as p:
                        try:
                            browser = p.chromium.launch(headless=True)
                        except Exception:
                            task_state.log("... Attempting to install Playwright browsers...")
                            os.system("playwright install")
                            browser = p.chromium.launch(headless=True)

                        context = browser.new_context(
                            viewport={"width": 1920, "height": 1080},
                            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                            locale="en-US,en;q=0.9"
                        )
                        page = context.new_page()

                        for i, url in enumerate(urls):
                            task_state.log(f"▶️  Processing URL ({i + 1}/{len(urls)}): {url}")
                            try:
                                should_check_cookie = handle_cookie and (i == 0)
                                result_paths = _take_screenshot_on_page(
                                    page=page,
                                    url=url,
                                    base_folder="screenshots",
                                    site_name=site_name,
                                    full_page=full_page,
                                    visible_only=visible_page,
                                    save_mhtml=save_mhtml,
                                    use_1280_width=use_1280_width,
                                    handle_cookie=should_check_cookie,
                                    cookie_button_text=cookie_button_text,
                                    log_func=task_state.log
                                )
                                for path in result_paths:
                                    task_state.log(f"  ✅ File saved: {os.path.basename(path)}")
                                successful_paths.extend(result_paths)
                            except Exception as e:
                                task_state.log(f"❌ Error processing page {url}: {e}")

                        task_state.log("🚪 Closing browser...")
                        browser.close()

            if pdf_urls:
                task_state.log(f"--- Processing {len(pdf_urls)} PDF files ---")
                # --- NEW: Initialize a counter for PDF files ---
                pdf_counter = 1
                for url in pdf_urls:
                    task_state.log(f"▶️  Processing PDF ({pdf_counter}/{len(pdf_urls)}): {url}")
                    try:
                        # --- CHANGE: Pass the counter to the process_pdf function ---
                        result_paths = process_pdf(
                            url=url,
                            base_folder="screenshots",
                            site_name=site_name,
                            pdf_counter=pdf_counter,
                            take_visible_screenshot=visible_page,
                            save_as_is=save_pdf,
                            log_func=task_state.log
                        )
                        successful_paths.extend(result_paths)
                        # --- NEW: Increment the counter after processing ---
                        pdf_counter += 1
                    except Exception as e:
                        task_state.log(f"❌ Error processing PDF {url}: {e}")

            if successful_paths:
                task_state.log("☁️ Uploading files to Shared Drive...")
                try:
                    folder_link_url = upload_all_screenshots_to_shared_drive(root_dir)
                    if folder_link_url:
                        task_state.log(f"📁 Folder link: {folder_link_url}")
                        task_state.folder_link = folder_link_url
                    else:
                        task_state.log("⚠️ Could not retrieve folder link after upload.")
                except Exception as upload_e:
                    task_state.log(f"❌ Error during Google Drive upload: {upload_e}")
            else:
                task_state.log("⚠️ No files were created. Please check URLs and settings.")

        except Exception as e:
            task_state.log(f"❌ A critical error occurred in the task: {e}")
        finally:
            task_state.is_running = False
            task_state.log("🎉 Task finished.")

    threading.Thread(target=worker).start()
    return jsonify({"status": "started"})


@app.route("/status")
def status():
    """Endpoint to get the current task status."""
    return jsonify({
        "log": task_state.log_lines,
        "done": not task_state.is_running,
        "folder_link": task_state.folder_link
    })


@app.route("/download")
def download_zip():
    """Endpoint to download all created files as a zip archive."""
    screenshots_dir = "screenshots"
    if not os.path.exists(screenshots_dir) or not os.listdir(screenshots_dir):
        return "No files to download.", 404

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

