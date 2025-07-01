from google.auth.transport.requests import Request
from google.oauth2 import service_account

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

creds = service_account.Credentials.from_service_account_file(
    "path/to/your/service_account.json", scopes=SCOPES
)

creds.refresh(Request())
print("Access token:")
print(creds.token)
