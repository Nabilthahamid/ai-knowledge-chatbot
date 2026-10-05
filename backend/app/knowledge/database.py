import os

import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector


load_dotenv()


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://chatbot:chatbot@127.0.0.1:5432/knowledge_chatbot",
)

EMBEDDING_DIMENSION = 384


def initialize_database() -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        connection.execute("CREATE EXTENSION IF NOT EXISTS vector")

        connection.execute(
            f"""
            CREATE TABLE IF NOT EXISTS document_chunks (
                id BIGSERIAL PRIMARY KEY,
                document_name TEXT NOT NULL,
                stored_filename TEXT,
                chunk_index INTEGER NOT NULL,
                page_number INTEGER,
                chunk_text TEXT NOT NULL,
                embedding VECTOR({EMBEDDING_DIMENSION}) NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
            """
        )

        connection.execute(
            """
            ALTER TABLE document_chunks
            ADD COLUMN IF NOT EXISTS stored_filename TEXT
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_document_chunks_stored_filename
            ON document_chunks(stored_filename)
            """
        )

        connection.commit()


def get_connection():
    connection = psycopg.connect(DATABASE_URL)
    register_vector(connection)
    return connection
