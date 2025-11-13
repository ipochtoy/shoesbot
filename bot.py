import os
import sys
import socket
import fcntl

# Fix for pyzbar on macOS - must be before any pyzbar imports
if sys.platform == "darwin":
    zbar_lib = "/opt/homebrew/lib"
    if os.path.exists(zbar_lib):
        # Force override (not setdefault) to ensure pyzbar loads correctly
        current_dyld = os.environ.get("DYLD_LIBRARY_PATH", "")
        os.environ["DYLD_LIBRARY_PATH"] = f"{zbar_lib}:{current_dyld}".rstrip(":")


def acquire_lock():
    """Prevent multiple bot instances using file lock."""
    lock_file = '/tmp/shoesbot.lock'
    lock_fd = open(lock_file, 'w')
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_fd.write(str(os.getpid()))
        lock_fd.flush()
        return lock_fd
    except IOError:
        print("❌ ERROR: Another instance of bot.py is already running!")
        print("❌ Only ONE bot can run with this token.")
        print("❌ Stop other instances or run on server: ssh gcp-shoesbot 'sudo systemctl status shoesbot.service'")
        sys.exit(1)


from shoesbot.telegram_bot import build_app

if __name__ == "__main__":
    # Acquire lock to prevent duplicate instances
    lock = acquire_lock()
    
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
