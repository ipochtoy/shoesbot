"""Environment setup - must be imported before any pyzbar imports."""
import os
import sys

def setup_env():
    """Setup environment variables for macOS."""
    if sys.platform == "darwin":
        zbar_lib = "/opt/homebrew/lib"
        if os.path.exists(zbar_lib):
            current_dyld = os.environ.get("DYLD_LIBRARY_PATH", "")
            if zbar_lib not in current_dyld:
                os.environ["DYLD_LIBRARY_PATH"] = f"{zbar_lib}:{current_dyld}".rstrip(":")

# Auto-run on import
setup_env()

