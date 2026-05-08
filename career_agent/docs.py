from __future__ import annotations

from googleapiclient.discovery import build
from career_agent.auth import get_credentials


class DocsStore:
      def __init__(self, document_id: str) -> None:
                self.document_id = document_id
                self.service = build("docs", "v1", credentials=get_credentials())

      def add_research_tab(self, firm_name: str, content: str) -> None:
                title = f"R: {firm_name}"[:30]

          # 1. Check if tab already exists
                doc = self.service.documents().get(documentId=self.document_id).execute()
                tabs = doc.get("tabs", [])
                existing_tab_id = None
                for tab in tabs:
                              props = tab.get("tabProperties", {})
                              if props.get("title") == title:
                                                existing_tab_id = props.get("tabId")
                                                break

                          if not existing_tab_id:
                                        # 2. Create new tab
                                        body = {
                                                          "requests": [
                                                                                {
                                                                                                          "addDocumentTab": {
                                                                                                                                        "tabProperties": {
                                                                                                                                                                          "title": title,
                                                                                                                                                                          "iconEmoji": "\u2696\ufe0f",
                                                                                                                                          }
                                                                                                            }
                                                                                  }
                                                          ]
                                        }
                                        response = self.service.documents().batchUpdate(
                                            documentId=self.document_id, body=body
                                        ).execute()
                                        existing_tab_id = (
                                            response["replies"][0]["addDocumentTab"]["tabProperties"]["tabId"]
                                        )

                # 3. Write content to the tab
                requests = [
                    {
                        "insertText": {
                            "location": {
                                "index": 1,
                                "tabId": existing_tab_id,
                            },
                            "text": content + "\n\n",
                        }
                    }
                ]
                self.service.documents().batchUpdate(
                    documentId=self.document_id, body={"requests": requests}
                ).execute()
