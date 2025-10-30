#!/bin/bash
cd "$(dirname "$0")"
pkill -9 -f "bot.py" 2>/dev/null || true
sleep 1
DYLD_LIBRARY_PATH=/opt/homebrew/lib nohup .venv/bin/python -u bot.py > bot.log 2>&1 &
sleep 2
if pgrep -f "bot.py" >/dev/null; then
  echo "Bot started: $(pgrep -f 'bot.py')"
else
  echo "Failed to start"
  tail -n 20 bot.log
fi
