from __future__ import annotations
import platform
import os


def system_info() -> str:
    parts = []
    parts.append(f"python: {platform.python_version()}")
    parts.append(f"platform: {platform.platform()}")
    parts.append(f"pyzbar: {'set' if bool(os.environ.get('PYZBAR')) else 'auto'}")
    parts.append(f"GOOGLE_APPLICATION_CREDENTIALS: {'set' if os.getenv('GOOGLE_APPLICATION_CREDENTIALS') else 'unset'}")
    parts.append(f"LOG_LEVEL: {os.getenv('LOG_LEVEL','INFO')}")
    try:
        import cv2
        parts.append(f"opencv: {cv2.__version__}")
    except Exception:
        parts.append("opencv: not available")
    try:
        import pyzbar
        parts.append(f"pyzbar: {getattr(pyzbar, '__version__', 'available')}")
    except Exception:
        parts.append("pyzbar: not available")
    return "\n".join(parts)
