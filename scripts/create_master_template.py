from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SERVICE_ACCOUNT_FILE = "path/to/service_account.json"
SCOPES = ["https://www.googleapis.com/auth/drive"]

creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)

service = build("drive", "v3", credentials=creds)

file_metadata = {
    "name": "Quote Spreadsheet Template 2025",
    "mimeType": "application/vnd.google-apps.spreadsheet",
    "parents": ["folder_id_here"],
}
media = MediaFileUpload(
    "path/to/template.xlsx",
    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    resumable=True,
)

file = (
    service.files()
    .create(body=file_metadata, media_body=media, fields="id, webViewLink")
    .execute()
)

print("Upload done! ID:", file.get("id"))
print("Link:", file.get("webViewLink"))
