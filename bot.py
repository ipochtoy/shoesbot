import os
import sys

# Fix for pyzbar on macOS - must be before any pyzbar imports
if sys.platform == "darwin":
    zbar_lib = "/opt/homebrew/lib"
    if os.path.exists(zbar_lib):
        os.environ.setdefault("DYLD_LIBRARY_PATH", zbar_lib)

from shoesbot.telegram_bot import build_app

if __name__ == "__main__":
    app = build_app()
    mode = os.getenv("MODE", "polling").lower()
    if mode == "webhook":
        port = int(os.getenv("PORT", "8080"))
        url = os.getenv("WEBHOOK_URL")
        path = os.getenv("WEBHOOK_PATH", "tg")
        if not url:
            raise RuntimeError("WEBHOOK_URL not set")
        app.run_webhook(listen="0.0.0.0", port=port, url_path=path, webhook_url=f"{url}/{path}")
    else:
        app.run_polling()
