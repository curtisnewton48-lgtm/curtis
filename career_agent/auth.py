from __future__ import annotations

import json
import os

from google.oauth2 import service_account

SCOPES = [
          "https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/documents",
          "https://www.googleapis.com/auth/drive.file",
]


def get_credentials():
          raw_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
          if raw_json:
                        info = json.loads(raw_json)
                        return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)

          path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
          if not path:
                        raise RuntimeError("Set GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_APPLICATION_CREDENTIALS.")
                    return service_account.Credentials.from_service_account_file(path, scopes=SCOPES)
