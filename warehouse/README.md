# Warehouse Laravel

Telegram bot for barcode scanning with direct Pochtoy integration.

## Requirements

- PHP 8.1+
- MySQL 8.0+
- Composer
- zbar-tools (`brew install zbar` on macOS)

## Installation

```bash
# Install dependencies
composer install

# Copy config
cp .env.example .env

# Edit .env with your credentials
# - TELEGRAM_BOT_TOKEN
# - DB credentials
# - GEMINI_API_KEY or OPENAI_API_KEY

# Generate app key
php artisan key:generate

# Run migrations
php artisan migrate
```

## Running

```bash
# Start bot
php artisan bot:run
```

## Architecture

### Decoders (in order of speed)

1. **ZBar** - Fast local barcode decoder (requires zbar-tools)
2. **Gemini Flash** - Fast AI fallback for GG labels (recommended)
3. **OpenAI GPT-4o-mini** - Alternative AI fallback

### Flow

1. Receive photo from Telegram
2. Buffer photos (3 sec timeout, max 10 photos)
3. Run ZBar decoder
4. If no GG/Q codes found → try Gemini/OpenAI
5. Send directly to Pochtoy API
6. Send result to user

### Database

- `photo_batches` - batch metadata, barcodes, Pochtoy status
- `photos` - individual photos linked to batches

## Configuration

| Variable | Description |
|----------|-------------|
| TELEGRAM_BOT_TOKEN | Bot token from @BotFather |
| GEMINI_API_KEY | Google AI Studio API key |
| OPENAI_API_KEY | OpenAI API key (fallback) |
| POCHTOY_API_URL | Pochtoy API endpoint |
| POCHTOY_API_TOKEN | Pochtoy auth token |
| PHOTO_BUFFER_TIMEOUT | Seconds to wait for more photos (default: 3) |
| PHOTO_BUFFER_MAX | Max photos per batch (default: 10) |
