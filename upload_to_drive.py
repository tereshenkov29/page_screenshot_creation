import os
import mimetypes
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

SCOPES = ["https://www.googleapis.com/auth/drive.file"]  # доступ к файлам, созданным приложением

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


def create_folder(service, folder_name):
    file_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder"
    }
    folder = service.files().create(body=file_metadata, fields="id").execute()
    return folder.get("id")


def upload_file(service, file_path, folder_id):
    file_name = os.path.basename(file_path)
    mime_type = mimetypes.guess_type(file_path)[0]
    file_metadata = {"name": file_name, "parents": [folder_id]}
    media = MediaFileUpload(file_path, mimetype=mime_type)
    file = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    return file.get("id")


def upload_all_screenshots():
    service = authenticate()

    today = datetime.now().strftime("%Y%m%d")
    folder_name = f"ProperAccess_Screenshots_{today}"
    folder_id = create_folder(service, folder_name)

    folder_link = f"https://drive.google.com/drive/folders/{folder_id}"
    print(f"📁 Папка создана: {folder_link}")

    screenshot_dir = "screenshots"
    files = [f for f in os.listdir(screenshot_dir) if f.endswith(".png")]

    for file_name in files:
        file_path = os.path.join(screenshot_dir, file_name)
        upload_file(service, file_path, folder_id)
        print(f"✅ Загружено: {file_name}")

    print(f"🎉 Все скриншоты загружены. Папка: {folder_link}")
    return folder_link


if __name__ == "__main__":
    upload_all_screenshots()