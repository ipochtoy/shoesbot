from __future__ import annotations
import json
import os
from typing import Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
ADMIN_FILE = os.path.join(DATA_DIR, 'admin.json')
os.makedirs(DATA_DIR, exist_ok=True)


def get_admin_id() -> Optional[int]:
    env = os.getenv('ADMIN_CHAT_ID')
    if env:
        try:
            return int(env)
        except Exception:
            pass
    try:
        with open(ADMIN_FILE, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        v = data.get('admin_chat_id')
        return int(v) if v is not None else None
    except Exception:
        return None


def set_admin_id(chat_id: int) -> None:
    try:
        with open(ADMIN_FILE, 'w', encoding='utf-8') as fh:
            json.dump({'admin_chat_id': int(chat_id)}, fh)
    except Exception:
        pass
