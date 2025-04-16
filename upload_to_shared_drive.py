import os
import mimetypes
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# Вставь сюда ID папки в Shared Drive
SHARED_DRIVE_FOLDER_ID = "179M2NAGyv5kNnVNrMUVsregISp7FcejD"  # ← замени на свой

def authenticate():
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

def create_subfolder(service, parent_folder_id, subfolder_name):
    metadata = {
        "name": subfolder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_folder_id]
    }

    folder = service.files().create(
        body=metadata,
        fields="id",
        supportsAllDrives=True
    ).execute()

    return folder.get("id")

def upload_file(service, file_path, folder_id):
    file_name = os.path.basename(file_path)
    mime_type = mimetypes.guess_type(file_path)[0]
    metadata = {
        "name": file_name,
        "parents": [folder_id]
    }

    media = MediaFileUpload(file_path, mimetype=mime_type)

    file = service.files().create(
        body=metadata,
        media_body=media,
        fields="id",
        supportsAllDrives=True
    ).execute()

    return file.get("id")

def upload_all_screenshots_to_shared_drive():
    service = authenticate()

    today = datetime.now().strftime("%Y%m%d")
    subfolder_name = f"Screenshots_{today}"
    upload_folder_id = create_subfolder(service, SHARED_DRIVE_FOLDER_ID, subfolder_name)

    folder_link = f"https://drive.google.com/drive/folders/{upload_folder_id}"
    print(f"📁 Подпапка создана: {folder_link}")

    screenshot_dir = "screenshots"
    files = [f for f in os.listdir(screenshot_dir) if f.endswith(".png")]

    for file_name in files:
        file_path = os.path.join(screenshot_dir, file_name)
        upload_file(service, file_path, upload_folder_id)
        print(f"✅ Загружено: {file_name}")

    print(f"🎉 Все скриншоты отправлены в Shared Drive: {folder_link}")
    return folder_link


if __name__ == "__main__":
    upload_all_screenshots_to_shared_drive()
