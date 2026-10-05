import numpy as np

from app.knowledge.database import (
    get_connection,
    initialize_database,
)


def save_chunks(
    document_name: str,
    stored_filename: str,
    chunks: list[dict],
    embeddings,
) -> None:
    if len(chunks) != len(embeddings):
        raise ValueError(
            "The number of chunks and embeddings must be equal"
        )

    initialize_database()

    with get_connection() as connection:
        for chunk, embedding in zip(chunks, embeddings):
            vector = np.asarray(
                embedding,
                dtype=np.float32,
            )

            connection.execute(
                """
                INSERT INTO document_chunks (
                    document_name,
                    stored_filename,
                    chunk_index,
                    page_number,
                    chunk_text,
                    embedding
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    document_name,
                    stored_filename,
                    chunk["chunk_index"],
                    chunk.get("page_number"),
                    chunk["text"],
                    vector,
                ),
            )

        connection.commit()


def search_similar(
    query_embedding,
    top_k: int = 5,
) -> list[dict]:
    initialize_database()

    query_vector = np.asarray(
        query_embedding,
        dtype=np.float32,
    )

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                document_name,
                chunk_index,
                page_number,
                chunk_text,
                1 - (embedding <=> %s) AS similarity
            FROM document_chunks
            ORDER BY embedding <=> %s
            LIMIT %s
            """,
            (
                query_vector,
                query_vector,
                top_k,
            ),
        ).fetchall()

    return [
        {
            "id": row[0],
            "document_name": row[1],
            "chunk_index": row[2],
            "page_number": row[3],
            "text": row[4],
            "similarity": float(row[5]),
        }
        for row in rows
    ]
