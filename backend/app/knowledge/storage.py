from pathlib import Path
from uuid import uuid4


UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def save_uploaded_file(original_filename: str, file_content: bytes) -> Path:
    safe_filename = Path(original_filename).name
    unique_filename = f"{uuid4().hex}_{safe_filename}"

    file_path = UPLOAD_DIR / unique_filename
    file_path.write_bytes(file_content)

    return file_path