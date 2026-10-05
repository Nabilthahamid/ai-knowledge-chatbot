from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.knowledge.embedding_service import (
    embed_documents,
    embed_query,
)
from app.knowledge.pdf_extractor import extract_pdf_pages
from app.knowledge.storage import save_uploaded_file
from app.knowledge.text_processor import clean_text, chunk_text
from app.knowledge.vector_store import (
    save_chunks,
    search_similar,
)


router = APIRouter(
    prefix="/api/v1/knowledge",
    tags=["Knowledge Base"],
)


MAX_FILE_SIZE = 10 * 1024 * 1024


@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="A file is required",
        )

    file_extension = Path(file.filename).suffix.lower()

    allowed_extensions = {".txt", ".pdf"}

    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Only TXT and PDF files are supported",
        )

    file_content = await file.read()

    if not file_content:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty",
        )

    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File size cannot exceed 10 MB",
        )

    saved_path = save_uploaded_file(
        original_filename=file.filename,
        file_content=file_content,
    )

    try:
        all_chunks = []
        total_character_count = 0
        page_count = None

        if file_extension == ".txt":
            raw_text = file_content.decode("utf-8")
            cleaned_text = clean_text(raw_text)

            total_character_count = len(cleaned_text)

            text_chunks = chunk_text(cleaned_text)

            for chunk in text_chunks:
                chunk["page_number"] = None
                all_chunks.append(chunk)

        elif file_extension == ".pdf":
            pages = extract_pdf_pages(file_content)
            page_count = len(pages)

            global_chunk_index = 0

            for page in pages:
                page_number = page["page_number"]
                page_text = clean_text(page["text"])

                if not page_text:
                    continue

                total_character_count += len(page_text)

                page_chunks = chunk_text(page_text)

                for chunk in page_chunks:
                    chunk["chunk_index"] = global_chunk_index
                    chunk["page_number"] = page_number

                    all_chunks.append(chunk)
                    global_chunk_index += 1

        if not all_chunks:
            saved_path.unlink(missing_ok=True)

            raise HTTPException(
                status_code=400,
                detail="No readable text was found",
            )

        chunk_texts = [
            chunk["text"]
            for chunk in all_chunks
        ]

        embeddings = embed_documents(chunk_texts)

        save_chunks(
            document_name=file.filename,
            stored_filename=saved_path.name,
            chunks=all_chunks,
            embeddings=embeddings,
        )

        return {
            "message": "Document uploaded and indexed successfully",
            "original_filename": file.filename,
            "file_type": file_extension.replace(".", ""),
            "stored_filename": saved_path.name,
            "page_count": page_count,
            "character_count": total_character_count,
            "chunk_count": len(all_chunks),
            "embedding_dimension": 384,
            "indexed": True,
            "chunks": all_chunks,
        }

    except UnicodeDecodeError as error:
        saved_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=400,
            detail="TXT files must use UTF-8 encoding",
        ) from error

    except HTTPException:
        raise

    except Exception as error:
        saved_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=500,
            detail=f"Could not process and index document: {error}",
        ) from error


@router.get("/search")
def search_knowledge_base(
    query: str = Query(..., min_length=2),
    top_k: int = Query(5, ge=1, le=20),
):
    try:
        query_embedding = embed_query(query)

        results = search_similar(
            query_embedding=query_embedding,
            top_k=top_k,
        )

        return {
            "query": query,
            "result_count": len(results),
            "results": results,
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {error}",
        ) from error
