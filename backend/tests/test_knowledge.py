from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_upload_text_document():
    file_content = (
        b"Python is a programming language. "
        b"FastAPI is a Python web framework."
    )

    response = client.post(
        "/api/v1/knowledge/documents/upload",
        files={
            "file": (
                "sample.txt",
                file_content,
                "text/plain",
            )
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["original_filename"] == "sample.txt"
    assert data["chunk_count"] >= 1
    assert len(data["chunks"]) >= 1

    stored_filename = data["stored_filename"]

    list_response = client.get(
        "/api/v1/admin/documents"
    )
    assert list_response.status_code == 200

    uploaded_document = next(
        document
        for document in list_response.json()["documents"]
        if document["filename"] == stored_filename
    )
    assert uploaded_document["original_filename"] == "sample.txt"
    assert uploaded_document["chunk_count"] == data["chunk_count"]

    delete_response = client.delete(
        f"/api/v1/admin/documents/{stored_filename}"
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["file_deleted"] is True
    assert (
        delete_response.json()["deleted_chunks"]
        == data["chunk_count"]
    )


def test_reject_unsupported_file():
    response = client.post(
        "/api/v1/knowledge/documents/upload",
        files={
            "file": (
                "sample.docx",
                b"fake docx content",
                "application/octet-stream",
            )
        },
    )

    assert response.status_code == 400
    assert "Only TXT and PDF files" in response.json()["detail"]
