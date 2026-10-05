from psycopg.types.json import Jsonb

from app.knowledge.database import (
    get_connection,
    initialize_database,
)


def initialize_chat_tables():
    """
    Create chat-related database tables.
    """

    initialize_database()

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id BIGSERIAL PRIMARY KEY,
                    title TEXT NOT NULL DEFAULT 'New conversation',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id BIGSERIAL PRIMARY KEY,
                    session_id BIGINT NOT NULL
                        REFERENCES chat_sessions(id)
                        ON DELETE CASCADE,
                    role TEXT NOT NULL
                        CHECK (role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    citations JSONB NOT NULL DEFAULT '[]'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_chat_messages_session_id
                ON chat_messages(session_id);
                """
            )

        connection.commit()


def create_session(title: str = "New conversation") -> dict:
    initialize_chat_tables()

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO chat_sessions (title)
                VALUES (%s)
                RETURNING id, title, created_at, updated_at;
                """,
                (title,),
            )

            row = cursor.fetchone()

        connection.commit()

    return {
        "id": row[0],
        "title": row[1],
        "created_at": row[2],
        "updated_at": row[3],
    }


def list_sessions() -> list[dict]:
    initialize_chat_tables()

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM chat_sessions
                ORDER BY updated_at DESC;
                """
            )

            rows = cursor.fetchall()

    return [
        {
            "id": row[0],
            "title": row[1],
            "created_at": row[2],
            "updated_at": row[3],
        }
        for row in rows
    ]


def session_exists(session_id: int) -> bool:
    initialize_chat_tables()

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1
                FROM chat_sessions
                WHERE id = %s;
                """,
                (session_id,),
            )

            return cursor.fetchone() is not None


def add_message(
    session_id: int,
    role: str,
    content: str,
    citations: list | None = None,
) -> dict:
    initialize_chat_tables()

    citations = citations or []

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO chat_messages
                    (session_id, role, content, citations)
                VALUES (%s, %s, %s, %s)
                RETURNING id, session_id, role,
                          content, citations, created_at;
                """,
                (
                    session_id,
                    role,
                    content,
                    Jsonb(citations),
                ),
            )

            row = cursor.fetchone()

            cursor.execute(
                """
                UPDATE chat_sessions
                SET updated_at = NOW()
                WHERE id = %s;
                """,
                (session_id,),
            )

        connection.commit()

    return {
        "id": row[0],
        "session_id": row[1],
        "role": row[2],
        "content": row[3],
        "citations": row[4],
        "created_at": row[5],
    }


def get_messages(session_id: int) -> list[dict]:
    initialize_chat_tables()

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, session_id, role,
                       content, citations, created_at
                FROM chat_messages
                WHERE session_id = %s
                ORDER BY created_at ASC, id ASC;
                """,
                (session_id,),
            )

            rows = cursor.fetchall()

    return [
        {
            "id": row[0],
            "session_id": row[1],
            "role": row[2],
            "content": row[3],
            "citations": row[4],
            "created_at": row[5],
        }
        for row in rows
    ]