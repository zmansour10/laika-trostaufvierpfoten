"""Read private configuration consistently in Streamlit Cloud and locally."""

import os
from pathlib import Path

from dotenv import dotenv_values
import streamlit as st


ENV_PATH = Path(__file__).resolve().parent / ".env"


def read_setting(name: str, *, aliases: tuple[str, ...] = (), strip: bool = False) -> str | None:
    """Prefer Streamlit Secrets, then environment variables, then local .env.

    Missing local secrets files are normal. Only non-empty strings are usable;
    access-key whitespace is preserved unless the caller explicitly strips it.
    """
    names = (name, *aliases)

    def usable(value: object) -> str | None:
        if not isinstance(value, str):
            return None
        value = value.strip() if strip else value
        return value if value else None

    for key in names:
        try:
            value = usable(st.secrets[key])
        except (FileNotFoundError, KeyError):
            continue
        if value is not None:
            return value

    for key in names:
        value = usable(os.environ.get(key))
        if value is not None:
            return value

    local_values = dotenv_values(ENV_PATH)
    for key in names:
        value = usable(local_values.get(key))
        if value is not None:
            return value
    return None
