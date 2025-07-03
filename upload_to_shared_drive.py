import os
import mimetypes
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# Укажи ID папки в Shared Drive
SHARED_DRIVE_FOLDER_ID = "179M2NAGyv5kNnVNrMUVsregISp7FcejD"  # ← замени на актуальный


def authenticate():
    """Обрабатывает аутентификацию с Google API."""
    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    return build("drive", "v3", credentials=creds)


def create_subfolder(service, parent_id, name):
    """Создает подпапку в указанной родительской папке на Google Drive."""
    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id]
    }
    folder = service.files().create(
        body=metadata,
        fields="id",
        supportsAllDrives=True
    ).execute()
    return folder["id"]


def upload_file(service, file_path, folder_id):
    """Загружает один файл в указанную папку на Google Drive."""
    file_name = os.path.basename(file_path)

    # --- УЛУЧШЕНИЕ: Более надежное определение MIME-типа ---
    mime_type, _ = mimetypes.guess_type(file_path)
    # Mimetypes может не знать о .mhtml, предоставляем фолбэк
    if file_name.endswith(".mhtml") and not mime_type:
        mime_type = "multipart/related"  # или "application/x-mimearchive"
    if not mime_type:
        mime_type = 'application/octet-stream'  # Стандартный тип для неизвестных данных

    metadata = {
        "name": file_name,
        "parents": [folder_id]
    }

    media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
    service.files().create(
        body=metadata,
        media_body=media,
        fields="id",
        supportsAllDrives=True
    ).execute()


def upload_all_screenshots_to_shared_drive(root_dir: str):
    """Загружает все содержимое локальной директории в новую папку на Shared Drive."""
    try:
        service = authenticate()
    except Exception as e:
        print(f"❌ Ошибка аутентификации: {e}")
        return None

    root_folder_name = os.path.basename(root_dir)
    main_folder_id = create_subfolder(service, SHARED_DRIVE_FOLDER_ID, root_folder_name)

    folder_link = f"https://drive.google.com/drive/folders/{main_folder_id}"
    print(f"📁 Основная папка создана: {folder_link}")

    for subfolder_name in os.listdir(root_dir):
        subfolder_path = os.path.join(root_dir, subfolder_name)
        if os.path.isdir(subfolder_path):
            subfolder_id = create_subfolder(service, main_folder_id, subfolder_name)
            for file_name in os.listdir(subfolder_path):
                # --- ИЗМЕНЕНИЕ: Теперь загружаем .png, .mhtml и .pdf ---
                if file_name.endswith((".png", ".mhtml", ".pdf")):
                    file_path = os.path.join(subfolder_path, file_name)
                    try:
                        upload_file(service, file_path, subfolder_id)
                        print(f"✅ Загружено: {file_name}")
                    except Exception as e:
                        print(f"❌ Не удалось загрузить {file_name}. Ошибка: {e}")

    print(f"🎉 Все файлы успешно загружены в: {folder_link}")
    return folder_link


if __name__ == "__main__":
    print("🚫 Этот скрипт предназначен для использования как модуль.")
