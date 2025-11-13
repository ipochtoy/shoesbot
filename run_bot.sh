#!/bin/bash
cd /Users/dzianismazol/Projects/shoesbot
export DYLD_LIBRARY_PATH=/opt/homebrew/lib
export PYTHONPATH=/Users/dzianismazol/Projects/shoesbot
exec .venv/bin/python shoesbot/telegram_bot.py



