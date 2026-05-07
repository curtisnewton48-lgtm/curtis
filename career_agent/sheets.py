from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/documents",
]


def _credentials():
    raw_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if raw_json:
        info = json.loads(raw_json)
        return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)

    path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not path:
        raise RuntimeError("Set GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_APPLICATION_CREDENTIALS.")
    return service_account.Credentials.from_service_account_file(path, scopes=SCOPES)


class SheetsStore:
    def __init__(self, spreadsheet_id: str) -> None:
        self.spreadsheet_id = spreadsheet_id
        self.service = build("sheets", "v4", credentials=_credentials())

    def values(self, range_name: str) -> list[list[str]]:
        result = (
            self.service.spreadsheets()
            .values()
            .get(spreadsheetId=self.spreadsheet_id, range=range_name)
            .execute()
        )
        return result.get("values", [])

    def profile(self) -> dict[str, str]:
        rows = self.values("Profile!A2:C100")
        return {row[0]: row[1] if len(row) > 1 else "" for row in rows if row}

    def target_companies(self) -> list[dict[str, str]]:
        rows = self.values("TargetCompanies!A2:H500")
        companies = []
        for row in rows:
            padded = row + [""] * (8 - len(row))
            if padded[0] or padded[1]:
                companies.append(
                    {
                        "company": padded[0],
                        "careers_url": padded[1],
                        "preferred": padded[2],
                        "notes": padded[3],
                        "source_type": padded[6] or "career_page",
                        "keywords": padded[7],
                    }
                )
        return companies

    def existing_job_ids(self) -> set[str]:
        rows = self.values("Jobs!A2:A2000")
        return {row[0] for row in rows if row}

    def append_jobs(self, jobs: list[dict[str, Any]]) -> None:
        if not jobs:
            return
        now = datetime.now(timezone.utc).isoformat()
        rows = [
            [
                job.get("job_id", ""),
                job.get("title", ""),
                job.get("company", ""),
                job.get("location", ""),
                job.get("remote", ""),
                job.get("salary", ""),
                job.get("url", ""),
                job.get("date_posted", ""),
                job.get("found_at", now),
                job.get("source", ""),
                job.get("status", "new"),
                job.get("fit_score", ""),
                job.get("role_type", ""),
                job.get("practice_area", ""),
                job.get("application_deadline", ""),
                job.get("eligibility", ""),
                job.get("fit_summary", ""),
                job.get("risks", ""),
                job.get("recommended_action", ""),
                job.get("tailored_pitch", ""),
                job.get("raw_description", ""),
                now,
            ]
            for job in jobs
        ]
        (
            self.service.spreadsheets()
            .values()
            .append(
                spreadsheetId=self.spreadsheet_id,
                range="Jobs!A:V",
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body={"values": rows},
            )
            .execute()
        )


class DocsStore:
    def __init__(self, document_id: str) -> None:
        self.document_id = document_id
        self.service = build("docs", "v1", credentials=_credentials())

    def append_research(self, jobs: list[dict[str, Any]]) -> None:
        if not self.document_id or not jobs:
            return
        text = "\n".join(_research_entry(job) for job in jobs)
        if not text.strip():
            return
        document = self.service.documents().get(documentId=self.document_id).execute()
        end_index = document["body"]["content"][-1]["endIndex"] - 1
        self.service.documents().batchUpdate(
            documentId=self.document_id,
            body={
                "requests": [
                    {
                        "insertText": {
                            "location": {"index": end_index},
                            "text": "\n\n" + text,
                        }
                    }
                ]
            },
        ).execute()


def _research_entry(job: dict[str, Any]) -> str:
    return (
        f"{job.get('company', 'Unknown firm')} - {job.get('title', 'Unknown role')}\n"
        f"URL: {job.get('url', '')}\n"
        f"Role type: {job.get('role_type', '')}\n"
        f"Practice area: {job.get('practice_area', '')}\n"
        f"Deadline: {job.get('application_deadline', '')}\n"
        f"Eligibility: {job.get('eligibility', '')}\n"
        f"Research: {job.get('firm_research', '')}\n"
        f"Fit summary: {job.get('fit_summary', '')}\n"
    )
