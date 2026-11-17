"""Persist reviewed letters without overwriting existing reference files."""

import hashlib
import os
from pathlib import Path
import tempfile


LETTERS_PATH = Path(__file__).resolve().parent / "data" / "letters"


class LetterSaveError(Exception):
    """A user-facing failure to save a reviewed letter."""


def save_letter(text: str, letters_dir: Path | None = None) -> Path:
    """Atomically publish exact UTF-8 content; repeat saves reuse the same file."""
    if not text.strip():
        raise LetterSaveError("Enter some letter text before saving.")
    directory = letters_dir if letters_dir is not None else LETTERS_PATH
    temporary_path = None
    try:
        content = text.encode("utf-8")
        digest = hashlib.sha256(content).hexdigest()
        # Content-derived names deduplicate repeated saves across sessions and dates.
        destination = directory / f"letter_saved_{digest}.txt"
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=directory, prefix=".letter_", suffix=".tmp", delete=False) as handle:
            temporary_path = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            # Publish a complete file exclusively, including across concurrent sessions.
            os.link(temporary_path, destination)
        except FileExistsError:
            if destination.read_bytes() != content:
                raise LetterSaveError("An existing letter conflicts with this filename. No file was overwritten.") from None
        return destination
    except (OSError, UnicodeError):
        raise LetterSaveError("Could not save the letter to data/letters/. Check folder permissions and disk space, then try again.") from None
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass  # An unpublished .tmp file is never loaded as a reference.
