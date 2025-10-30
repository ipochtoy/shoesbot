from __future__ import annotations
import json
import os
import time
from typing import Any, Dict, Iterable, Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
METRICS_FILE = os.path.join(DATA_DIR, 'metrics.jsonl')
MAX_BYTES = 5_000_000  # 5 MB

os.makedirs(DATA_DIR, exist_ok=True)


def _rotate_if_needed(path: str) -> None:
    try:
        if os.path.exists(path) and os.path.getsize(path) > MAX_BYTES:
            for i in range(3, 0, -1):
                src = f"{path}.{i}"
                dst = f"{path}.{i+1}"
                if os.path.exists(src):
                    if i == 3:
                        try:
                            os.remove(src)
                        except Exception:
                            pass
                    else:
                        try:
                            os.rename(src, dst)
                        except Exception:
                            pass
            try:
                os.rename(path, f"{path}.1")
            except Exception:
                pass
    except Exception:
        pass


def now_ts() -> float:
    return time.time()


def append_event(event: Dict[str, Any]) -> None:
    event = dict(event)
    event.setdefault('ts', now_ts())
    _rotate_if_needed(METRICS_FILE)
    try:
        with open(METRICS_FILE, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + '\n')
    except Exception:
        pass


def tail_events(n: int = 100) -> list[Dict[str, Any]]:
    try:
        with open(METRICS_FILE, 'r', encoding='utf-8') as fh:
            lines = fh.readlines()[-n:]
        return [json.loads(l) for l in lines if l.strip()]
    except Exception:
        return []


def summarize(n: int = 500) -> Dict[str, Any]:
    evs = tail_events(n)
    total = len(evs)
    ok = sum(1 for e in evs if e.get('result_count', 0) > 0)
    empty = total - ok
    per_decoder: dict[str, int] = {}
    for e in evs:
        for t in e.get('timeline', []):
            per_decoder[t.get('decoder', 'unknown')] = per_decoder.get(t.get('decoder', 'unknown'), 0) + int(t.get('count', 0) > 0)
    return {
        'total': total,
        'ok': ok,
        'empty': empty,
        'per_decoder_hits': per_decoder,
    }
