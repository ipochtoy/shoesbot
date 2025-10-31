# 🚀 Service Management

## Current Setup

Bot runs as **launchd service** (macOS native).

**Location:**
- Service file: `~/Library/LaunchAgents/com.shoesbot.plist`
- Bot code: `~/Projects/shoesbot/`
- Logs: `~/Projects/shoesbot/bot.log`

## Commands

### Check if running
```bash
ps aux | grep bot.py | grep -v grep
```

### View logs
```bash
tail -f ~/Projects/shoesbot/bot.log
```

### Restart service
```bash
launchctl unload ~/Library/LaunchAgents/com.shoesbot.plist
launchctl load ~/Library/LaunchAgents/com.shoesbot.plist
```

### Stop service
```bash
launchctl unload ~/Library/LaunchAgents/com.shoesbot.plist
```

### Start service
```bash
launchctl load ~/Library/LaunchAgents/com.shoesbot.plist
```

### Uninstall service
```bash
launchctl unload ~/Library/LaunchAgents/com.shoesbot.plist
rm ~/Library/LaunchAgents/com.shoesbot.plist
```

## Automatic Features

✅ Auto-starts after Mac reboot
✅ Auto-restarts if bot crashes
✅ Runs in background
✅ Logs to `bot.log`

## Quick Start Script

If service fails, use manual start:

```bash
cd ~/Projects/shoesbot
./START.sh
```

## Troubleshooting

### Bot not starting
Check logs:
```bash
tail -n 50 ~/Projects/shoesbot/bot.log
```

### Service not loading
Check service file:
```bash
launchctl list | grep shoesbot
```

### Reload after code changes
```bash
cd ~/Projects/shoesbot
git pull  # or your deployment method
./START.sh
```

