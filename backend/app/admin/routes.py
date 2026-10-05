from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.knowledge.database import (
    get_connection,
    initialize_database,
)


router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Admin"],
)


UPLOAD_DIRECTORY = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "uploads"
)


ALLOWED_EXTENSIONS = {
    ".txt",
    ".pdf",
}


@router.get("/documents")
def list_documents():
    initialize_database()

    UPLOAD_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    documents = []

    with get_connection() as connection:
        with connection.cursor() as cursor:
            for file_path in sorted(
                UPLOAD_DIRECTORY.iterdir()
            ):
                if not file_path.is_file():
                    continue

                if (
                    file_path.suffix.lower()
                    not in ALLOWED_EXTENSIONS
                ):
                    continue

                cursor.execute(
                    """
                    SELECT document_name, COUNT(*)
                    FROM document_chunks
                    WHERE stored_filename = %s
                    GROUP BY document_name;
                    """,
                    (file_path.name,),
                )

                row = cursor.fetchone()
                original_filename = (
                    row[0]
                    if row
                    else file_path.name.split("_", 1)[-1]
                )
                chunk_count = row[1] if row else 0
                file_stats = file_path.stat()

                documents.append(
                    {
                        "filename": file_path.name,
                        "original_filename": original_filename,
                        "extension": file_path.suffix.lower(),
                        "size_bytes": file_stats.st_size,
                        "chunk_count": chunk_count,
                        "modified_at": file_stats.st_mtime,
                    }
                )

    return {
        "documents": documents
    }


@router.delete("/documents/{filename}")
def delete_document(filename: str):
    safe_filename = Path(filename).name

    if safe_filename != filename:
        raise HTTPException(
            status_code=400,
            detail="Invalid filename",
        )

    file_path = (
        UPLOAD_DIRECTORY / safe_filename
    )

    initialize_database()

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM document_chunks
                WHERE stored_filename = %s;
                """,
                (safe_filename,),
            )

            deleted_chunks = cursor.rowcount

        connection.commit()

    file_deleted = False

    if file_path.exists():
        file_path.unlink()
        file_deleted = True

    return {
        "filename": safe_filename,
        "file_deleted": file_deleted,
        "deleted_chunks": deleted_chunks,
    }
