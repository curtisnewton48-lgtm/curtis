from career_agent.sheets import DocsStore


class _Execute:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def execute(self) -> dict:
        return self.payload


class FakeDocumentsResource:
    def __init__(self) -> None:
        self.batch_updates = []
        self.fail_tab_create = False

    def get(self, documentId: str) -> _Execute:
        return _Execute({"body": {"content": [{"endIndex": 1}, {"endIndex": 42}]}})

    def batchUpdate(self, documentId: str, body: dict) -> _Execute:
        self.batch_updates.append({"documentId": documentId, "body": body})
        if body["requests"][0].get("addDocumentTab"):
            if self.fail_tab_create:
                raise RuntimeError("Tabs unavailable")
            return _Execute(
                {
                    "replies": [
                        {
                            "addDocumentTab": {
                                "tabProperties": {
                                    "tabId": "tab-123",
                                    "title": body["requests"][0]["addDocumentTab"]["tabProperties"]["title"],
                                }
                            }
                        }
                    ]
                }
            )
        return _Execute({})


class FakeDocsService:
    def __init__(self) -> None:
        self.documents_resource = FakeDocumentsResource()

    def documents(self) -> FakeDocumentsResource:
        return self.documents_resource


class FakeDriveFiles:
    def __init__(self) -> None:
        self.created = []

    def create(self, body: dict, fields: str) -> _Execute:
        self.created.append({"body": body, "fields": fields})
        return _Execute({"id": "new-doc", "webViewLink": "https://docs.google.com/document/d/new-doc/edit"})


class FakeDriveService:
    def __init__(self) -> None:
        self.files_resource = FakeDriveFiles()

    def files(self) -> FakeDriveFiles:
        return self.files_resource


def _store(document_id: str = "", folder_id: str = "") -> DocsStore:
    store = DocsStore.__new__(DocsStore)
    store.document_id = document_id
    store.folder_id = folder_id
    store.service = FakeDocsService()
    store.drive_service = FakeDriveService()
    return store


def test_create_research_doc_adds_master_tab_when_document_id_exists() -> None:
    store = _store(document_id="master-doc", folder_id="research-folder")

    url = store.create_research_doc("Shelter - Paralegal Research", "Comprehensive research.")

    assert url == "https://docs.google.com/document/d/master-doc/edit?tab=tab-123"
    assert store.drive_service.files_resource.created == []
    tab_request = store.service.documents_resource.batch_updates[0]["body"]["requests"][0]
    assert tab_request["addDocumentTab"]["tabProperties"]["title"] == "Shelter - Paralegal Research"
    request = store.service.documents_resource.batch_updates[1]["body"]["requests"][0]
    assert request["insertText"]["location"] == {"index": 1, "tabId": "tab-123"}
    assert "Shelter - Paralegal Research" in request["insertText"]["text"]
    assert "Comprehensive research." in request["insertText"]["text"]


def test_create_research_doc_falls_back_to_master_append_when_tabs_fail() -> None:
    store = _store(document_id="master-doc", folder_id="research-folder")
    store.service.documents_resource.fail_tab_create = True

    url = store.create_research_doc("Shelter - Paralegal Research", "Comprehensive research.")

    assert url == "https://docs.google.com/document/d/master-doc/edit"
    request = store.service.documents_resource.batch_updates[1]["body"]["requests"][0]
    assert request["insertText"]["location"]["index"] == 41
    assert "Shelter - Paralegal Research" in request["insertText"]["text"]
    assert "Comprehensive research." in request["insertText"]["text"]


def test_create_research_doc_creates_file_when_no_master_document_exists() -> None:
    store = _store(folder_id="research-folder")

    url = store.create_research_doc("Shelter - Paralegal Research", "Comprehensive research.")

    assert url == "https://docs.google.com/document/d/new-doc/edit"
    created = store.drive_service.files_resource.created[0]["body"]
    assert created["name"] == "Shelter - Paralegal Research"
    assert created["parents"] == ["research-folder"]
