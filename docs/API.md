# Shoesbot API Documentation

This document provides comprehensive documentation for all API endpoints in the Shoesbot application.

## Table of Contents

1. [Upload & Buffer Management](#upload--buffer-management)
2. [Photo Management](#photo-management)
3. [AI & Enhancement](#ai--enhancement)
4. [Search & Barcodes](#search--barcodes)
5. [Admin & Webhooks](#admin--webhooks)

---

## Upload & Buffer Management

### POST /photos/api/upload-batch/

Upload a batch of photos from Telegram bot to create a product card.

**Purpose:** Primary endpoint for Telegram bot to upload photos and create a new product card. Automatically processes barcodes and sends to Pochtoy API.

**Request Parameters:**

Body (JSON):
- `correlation_id` (string, optional): Unique identifier for the batch. Auto-generated if not provided.
- `chat_id` (integer, required): Telegram chat ID.
- `message_ids` (array, optional): Array of Telegram message IDs.
- `photos` (array, required): Array of photo objects.
  - `file_id` (string, required): Telegram file ID.
  - `message_id` (integer, optional): Telegram message ID.
  - `image` (string, required): Base64-encoded image data.
- `barcodes` (array, optional): Array of barcode objects.
  - `photo_index` (integer): Index of the photo containing this barcode.
  - `symbology` (string): Barcode type (e.g., "EAN13", "CODE39").
  - `data` (string): Barcode value.
  - `source` (string): Detection source (e.g., "zbar", "opencv-qr").

**Request Example:**

```bash
curl -X POST http://localhost:8000/photos/api/upload-batch/ \
  -H "Content-Type: application/json" \
  -d '{
    "correlation_id": "abc12345",
    "chat_id": 123456789,
    "message_ids": [1001, 1002],
    "photos": [
      {
        "file_id": "AgACAgIAAxkBAAI...",
        "message_id": 1001,
        "image": "iVBORw0KGgoAAAANSUhEUgAA..."
      }
    ],
    "barcodes": [
      {
        "photo_index": 0,
        "symbology": "EAN13",
        "data": "1234567890123",
        "source": "zbar"
      }
    ]
  }'
```

**Response Format:**

Success (200):
```json
{
  "success": true,
  "correlation_id": "abc12345",
  "photos_saved": 3,
  "barcodes_saved": 2,
  "pochtoy_message": "✅ Товар успешно добавлен"
}
```

Error (400/500):
```json
{
  "error": "chat_id and photos required"
}
```

**Notes:**
- Images must be base64-encoded.
- Can include data URI prefix (e.g., `data:image/jpeg;base64,`) or just the base64 data.
- Automatically attempts to send to Pochtoy API after creation.
- CSRF exempt.

---

### POST /photos/api/buffer-upload/

Upload photo to buffer for manual sorting.

**Purpose:** Save photos to a buffer without immediate processing. Used by buffer bot for photos that need manual sorting/grouping.

**Request Parameters:**

Body (JSON):
- `file_id` (string, required): Telegram file ID.
- `message_id` (integer, required): Telegram message ID.
- `chat_id` (integer, required): Telegram chat ID.
- `image` (string, required): Base64-encoded image data.
- `gg_label` (string, optional): Pre-detected GG label (e.g., "GG747").

**Request Example:**

```bash
curl -X POST http://localhost:8000/photos/api/buffer-upload/ \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "AgACAgIAAxkBAAI...",
    "message_id": 2001,
    "chat_id": 123456789,
    "image": "iVBORw0KGgoAAAANSUhEUgAA...",
    "gg_label": "GG747"
  }'
```

**Response Format:**

Success (200):
```json
{
  "success": true,
  "photo_id": 42
}
```

Error (400/500):
```json
{
  "error": "Missing required fields"
}
```

**Notes:**
- Photos are saved without creating a product card.
- Duplicate file_ids are silently ignored (returns success).
- CSRF exempt.

---

### POST /photos/api/detect-gg-in-buffer/

Detect GG labels in all unprocessed buffer photos using OpenAI Vision.

**Purpose:** Batch process buffer photos to find GG/Q labels using AI vision.

**Request Parameters:** None

**Request Example:**

```bash
curl -X POST http://localhost:8000/photos/api/detect-gg-in-buffer/
```

**Response Format:**

Success (200):
```json
{
  "success": true,
  "found_count": 5
}
```

Error (500):
```json
{
  "error": "Error message"
}
```

**Notes:**
- Requires `OPENAI_API_KEY` environment variable.
- Only processes photos with empty `gg_label` field.
- Uses GPT-4o-mini model.
- CSRF exempt.

---

### POST /photos/api/clear-buffer/

Clear all unprocessed photos from buffer.

**Purpose:** Delete all unsorted photos and their physical files from the buffer.

**Request Parameters:** None

**Request Example:**

```bash
curl -X POST http://localhost:8000/photos/api/clear-buffer/
```

**Response Format:**

Success (200):
```json
{
  "success": true,
  "deleted_count": 15,
  "files_deleted": 15
}
```

Error (500):
```json
{
  "error": "Error message"
}
```

**Notes:**
- Only deletes photos with `processed=False`.
- Deletes both database records and physical image files.
- CSRF exempt.

---

### POST /photos/api/send-group-to-bot/{group_id}/

Create a product card from a buffer photo group.

**Purpose:** Convert a manually sorted group of buffer photos into a product card.

**Request Parameters:**

Path:
- `group_id` (integer, required): Buffer group ID.

**Request Example:**

```bash
curl -X POST http://localhost:8000/photos/api/send-group-to-bot/1/
```

**Response Format:**

Success (200):
```json
{
  "success": true,
  "correlation_id": "xyz78901",
  "photos_sent": 3,
  "card_created": true
}
```

Error (400/500):
```json
{
  "error": "Группа пуста"
}
```

**Notes:**
- Internally calls `upload-batch` to create the card.
- Marks buffer photos as processed.
- CSRF exempt.

---

### POST /photos/api/send-group-to-pochtoy/{group_id}/

Send buffer photo group directly to Pochtoy API.

**Purpose:** Send a group of buffer photos to Pochtoy without creating a local product card.

**Request Parameters:**

Path:
- `group_id` (integer, required): Buffer group ID.

**Request Example:**

```bash
curl -X POST http://localhost:8000/photos/api/send-group-to-pochtoy/1/
```

**Response Format:**

Success (200):
```json
{
  "success": true,
  "message": "Successfully sent to Pochtoy"
}
```

Error (400/500):
```json
{
  "error": "Группа пуста"
}
```

**Notes:**
- Does NOT mark photos as processed (can still create card later).
- Requires Pochtoy API integration configured.
- CSRF exempt.

---

### POST /photos/api/update-photo-group/{photo_id}/

Update the group ID for a buffer photo.

**Purpose:** Assign or change the group ID for manual photo sorting.

**Request Parameters:**

Path:
- `photo_id` (integer, required): Buffer photo ID.

Body (JSON):
- `group_id` (integer, nullable): Group ID to assign (null to ungroup).

**Request Example:**

```bash
curl -X POST http://localhost:8000/photos/api/update-photo-group/42/ \
  -H "Content-Type: application/json" \
  -d '{"group_id": 1}'
```

**Response Format:**

Success (200):
```json
{
  "success": true
}
```

Error (500):
```json
{
  "error": "Error message"
}
```

**Notes:**
- CSRF exempt.

---

### DELETE /photos/api/delete-buffer-photo/{photo_id}/

Delete a single photo from buffer.

**Purpose:** Remove an individual buffer photo and its file.

**Request Parameters:**

Path:
- `photo_id` (integer, required): Buffer photo ID.

**Request Example:**

```bash
curl -X DELETE http://localhost:8000/photos/api/delete-buffer-photo/42/
```

**Response Format:**

Success (200):
```json
{
  "success": true
}
```

Error (404/500):
```json
{
  "error": "Photo not found"
}
```

**Notes:**
- Deletes both database record and physical file.
- CSRF exempt.

---

### GET /photos/api/get-last-card/

Get information about the most recently created product card.

**Purpose:** Retrieve details of the last card for display or reference.

**Request Parameters:** None

**Request Example:**

```bash
curl -X GET http://localhost:8000/photos/api/get-last-card/
```

**Response Format:**

Success (200):
```json
{
  "correlation_id": "abc12345",
  "title": "Stone Island Sweater",
  "photos_count": 3,
  "uploaded_at": "2025-11-10T12:34:56.789Z"
}
```

No cards:
```json
{
  "correlation_id": null
}
```

**Notes:**
- CSRF exempt.
- Returns most recent by `uploaded_at`.

---

## Photo Management

### POST /photos/api/upload-photo-from-computer/{card_id}/

Upload a photo from local computer to a product card.

**Purpose:** Add photos to existing card via web interface file upload.

**Request Parameters:**

Path:
- `card_id` (integer, required): Product card ID.

Body (multipart/form-data):
- `photo` (file, required): Image file (max 10MB).

**Request Example:**

```bash
curl -X POST http://localhost:8000/photos/api/upload-photo-from-computer/5/ \
  -F "photo=@/path/to/image.jpg"
```

**Response Format:**

Success (200):
```json
{
  "success": true,
  "photo_id": 123,
  "photo_url": "/media/photos/2025/11/10/abc12345_upload_123.jpg"
}
```

Error (400/500):
```json
{
  "success": false,
  "error": "Фото не выбрано"
}
```

**Notes:**
- Accepts only image files (checked via content-type).
- Max file size: 10MB.
- Automatically converts to RGB JPEG.
- Photo is added to the end of the card's photo list.

---

### POST /photos/api/add-photo-from-url/{card_id}/

Add a photo to card from a URL.

**Purpose:** Download and add an external image to a product card (e.g., stock photos).

**Request Parameters:**

Path:
- `card_id` (integer, required): Product card ID.

Body (JSON):
- `url` (string, required): Image URL.

**Request Example:**

```bash
curl -X POST http://localhost:8000/photos/api/add-photo-from-url/5/ \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/stock-photo.jpg"
  }'
```

**Response Format:**

Success (200):
```json
{
  "success": true,
  "photo_id": 124,
  "photo_url": "/media/photos/2025/11/10/abc12345_stock_124.jpg"
}
```

Error (400/500):
```json
{
  "success": false,
  "error": "URL не указан"
}
```

**Notes:**
- HTTP URLs are automatically upgraded to HTTPS.
- Validates content-type is an image.
- Converts to RGB JPEG.
- Timeout: 15 seconds.
- CSRF exempt.

---

### POST /photos/api/set-main-photo/{photo_id}/

Set a photo as the main (primary) photo for its card.

**Purpose:** Mark a specific photo as the main/featured photo for the product card.

**Request Parameters:**

Path:
- `photo_id` (integer, required): Photo ID.

**Request Example:**

```bash
curl -X POST http://localhost:8000/photos/api/set-main-photo/123/
```

**Response Format:**

Success (200):
```json
{
  "success": true,
  "message": "Фото установлено как главное"
}
```

**Notes:**
- Automatically unsets any other main photo in the same card.
- CSRF exempt.

---

### POST /photos/api/move-photo/{photo_id}/

Move a photo up or down in the card's photo order.

**Purpose:** Reorder photos within a product card.

**Request Parameters:**

Path:
- `photo_id` (integer, required): Photo ID.

Body (JSON):
- `direction` (string, required): Either "up" or "down".

**Request Example:**

```bash
curl -X POST http://localhost:8000/photos/api/move-photo/123/ \
  -H "Content-Type: application/json" \
  -d '{"direction": "up"}'
```

**Response Format:**

Success (200):
```json
{
  "success": true,
  "message": "Фото перемещено вверх"
}
```

Error (400):
```json
{
  "success": false,
  "error": "Нельзя переместить в этом направлении"
}
```

**Notes:**
- Main photo always appears first.
- Cannot move beyond list boundaries.
- CSRF exempt.

---

### POST /photos/api/delete-photo/{photo_id}/

Delete a photo from a card.

**Purpose:** Remove a photo and its file from a product card.

**Request Parameters:**

Path:
- `photo_id` (integer, required): Photo ID.

**Request Example:**

```bash
curl -X POST http://localhost:8000/photos/api/delete-photo/123/
```

**Response Format:**

Success (200):
```json
{
  "success": true,
  "message": "Фото удалено"
}
```

**Notes:**
- Deletes both database record and physical file.
- Associated barcodes are deleted cascadingly.
- CSRF exempt.

---

### POST /photos/api/rotate-photo/{photo_id}/

Rotate a photo 90 degrees.

**Purpose:** Fix photo orientation.

**Request Parameters:**

Path:
- `photo_id` (integer, required): Photo ID.

Body (JSON):
- `direction` (string, optional): "left" (counter-clockwise) or "right" (clockwise, default).

**Request Example:**

```bash
curl -X POST http://localhost:8000/photos/api/rotate-photo/123/ \
  -H "Content-Type: application/json" \
  -d '{"direction": "right"}'
```

**Response Format:**

Success (200):
```json
{
  "success": true,
  "message": "Фото повернуто вправо",
  "data": {
    "photo_url": "/media/photos/2025/11/10/abc12345_123.jpg"
  }
}
```

**Notes:**
- Physically rotates the image file.
- Old file is deleted after rotation.
- CSRF exempt.

---

## AI & Enhancement

### POST /photos/api/generate-summary/{card_id}/

Generate AI summary of the product from photos and barcodes.

**Purpose:** Use OpenAI Vision to analyze product photos and create a comprehensive summary.

**Request Parameters:**

Path:
- `card_id` (integer, required): Product card ID.

**Request Example:**

```bash
curl -X POST http://localhost:8000/photos/api/generate-summary/5/
```

**Response Format:**

Success (200):
```json
{
  "success": true,
  "summary": "Stone Island crew neck sweater in black. Features the iconic compass badge on the left sleeve. Size XL. Excellent condition with no visible wear. Premium Italian craftsmanship with high-quality knit construction."
}
```

Error (400/500):
```json
{
  "success": false,
  "error": "Нет фото для анализа"
}
```

**Notes:**
- Requires `OPENAI_API_KEY` environment variable.
- Analyzes all photos in the card.
- Considers barcodes and GG labels.
- Summary is saved to `PhotoBatch.ai_summary`.
- Requires staff member authentication.

---

### POST /photos/api/generate-from-instruction/{card_id}/

Generate product description from voice/text instruction.

**Purpose:** Use AI to generate specific product information based on user instruction.

**Request Parameters:**

Path:
- `card_id` (integer, required): Product card ID.

Body (JSON):
- `instruction` (string, required): User instruction (e.g., "describe the color and material").

**Request Example:**

```bash
curl -X POST http://localhost:8000/photos/api/generate-from-instruction/5/ \
  -H "Content-Type: application/json" \
  -d '{
    "instruction": "What color and material is this item?"
  }'
```

**Response Format:**

Success (200):
```json
{
  "success": true,
  "result": "This item is black in color and appears to be made of high-quality cotton knit material with a soft texture."
}
```

Error (400/500):
```json
{
  "success": false,
  "error": "Instruction required"
}
```

**Notes:**
- Requires `OPENAI_API_KEY` environment variable.
- Analyzes photos based on instruction context.
- Requires staff member authentication.

---

### POST /photos/api/save-ai-summary/{card_id}/

Save or update AI-generated summary for a card.

**Purpose:** Manually save or edit the AI summary text.

**Request Parameters:**

Path:
- `card_id` (integer, required): Product card ID.

Body (JSON):
- `summary` (string, required): Summary text to save.

**Request Example:**

```bash
curl -X POST http://localhost:8000/photos/api/save-ai-summary/5/ \
  -H "Content-Type: application/json" \
  -d '{
    "summary": "Updated product summary text"
  }'
```

**Response Format:**

Success (200):
```json
{
  "success": true,
  "message": "Сводка сохранена"
}
```

**Notes:**
- CSRF exempt.
- Requires staff member authentication.

---

### POST /photos/api/enhance-photo/{photo_id}/

Enhance photo using FASHN AI (ghost mannequin or background change).

**Purpose:** Process product photo to add ghost mannequin effect or change background using FASHN AI.

**Request Parameters:**

Path:
- `photo_id` (integer, required): Photo ID.

Body (JSON):
- `mode` (string, optional): "ghost_mannequin" (default) or "product_beautifier".

**Request Example:**

```bash
curl -X POST http://localhost:8000/photos/api/enhance-photo/123/ \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "ghost_mannequin"
  }'
```

**Response Format:**

Success (200):
```json
{
  "success": true,
  "photo_id": 125,
  "photo_url": "/media/photos/2025/11/10/abc12345_enhanced_125.png",
  "message": "Фото обработано (ghost mannequin)",
  "reload": true
}
```

Error (400/500):
```json
{
  "success": false,
  "error": "Не удалось обработать фото"
}
```

**Notes:**
- Requires `CLOUDFLARED_URL` environment variable for public photo access.
- Creates a NEW photo (does not replace original).
- Uses FASHN AI API for processing.
- Ghost mannequin mode creates 1k resolution output.
- CSRF exempt.

---

## Search & Barcodes

### GET /photos/api/search-barcode/

Search for product information by barcode.

**Purpose:** Find product details and images using barcode via multiple sources (Google Lens, Google Shopping, Bing).

**Request Parameters:**

Query:
- `barcode` (string, required): Barcode to search.
- `card_id` (integer, optional): Card ID to use photos from for Google Lens search.

**Request Example:**

```bash
curl -X GET "http://localhost:8000/photos/api/search-barcode/?barcode=1234567890123&card_id=5"
```

**Response Format:**

Success (200):
```json
{
  "title": "Stone Island Sweater",
  "description": "Premium Italian knitwear...",
  "category": "Clothing",
  "brand": "Stone Island",
  "images": [
    "https://example.com/image1.jpg",
    "https://example.com/image2.jpg"
  ]
}
```

Error (400/500):
```json
{
  "error": "Barcode required"
}
```

**Notes:**
- Tries multiple sources: Google Lens/Vision API, Google Custom Search, Bing.
- If `card_id` provided, uses photos from that card for Google Lens.
- Requires API keys: `GOOGLE_VISION_API_KEY`, `GOOGLE_CUSTOM_SEARCH_API_KEY`, `GOOGLE_CUSTOM_SEARCH_ENGINE_ID`.
- CSRF exempt.

---

### GET /photos/api/search-stock-photos/{card_id}/

Search for stock photos of the product.

**Purpose:** Find high-quality stock photos from eBay, Google Lens, and other sources.

**Request Parameters:**

Path:
- `card_id` (integer, required): Product card ID.

Query:
- `barcode` (string, optional): Specific barcode to search.

**Request Example:**

```bash
curl -X GET "http://localhost:8000/photos/api/search-stock-photos/5/?barcode=1234567890123"
```

**Response Format:**

Success (200):
```json
{
  "success": true,
  "images": [
    {
      "url": "https://i.ebayimg.com/...",
      "thumbnail": "https://i.ebayimg.com/...",
      "title": "eBay ($250.00 USD)",
      "source": "ebay"
    },
    {
      "url": "https://example.com/stock.jpg",
      "thumbnail": "https://example.com/stock.jpg",
      "title": "Stone Island Sweater",
      "source": "google_lens"
    }
  ],
  "query": "Stone Island crew neck sweater black",
  "debug": {
    "total_found": 25,
    "filtered_out": 5,
    "final_count": 12,
    "sources": {
      "ebay": 3,
      "google_lens": 5,
      "google": 4
    },
    "version": "v4.0_simplified"
  }
}
```

**Notes:**
- Uses OpenAI Vision to identify product for better search results.
- Searches eBay, Google Lens (Vision API), and Google Custom Search.
- Filters out social media images (Instagram, Facebook, etc.).
- Returns max 12 images.
- CSRF exempt.

---

### POST /photos/api/reprocess-photo/{photo_id}/

Reprocess photo to detect barcodes and GG labels.

**Purpose:** Re-run barcode detection on a photo using all available decoders (ZBar, OpenCV, Google Vision, OpenAI).

**Request Parameters:**

Path:
- `photo_id` (integer, required): Photo ID.

**Request Example:**

```bash
curl -X POST http://localhost:8000/photos/api/reprocess-photo/123/
```

**Response Format:**

Success (200):
```json
{
  "success": true,
  "barcodes_found": 3,
  "barcodes": [
    "EAN13: 1234567890123 (zbar)",
    "CODE39: Q747 (google-vision-direct)",
    "CODE39: GG752 (openai-vision)"
  ],
  "total_results": 3,
  "api_info": [
    "Google Vision API: доступен",
    "OpenAI Vision: доступен"
  ],
  "debug_info": {
    "used_pipeline": "decoders",
    "google_vision_called": true,
    "openai_called": true
  }
}
```

**Notes:**
- Uses decoder pipeline if available, falls back to direct API calls.
- Requires staff member authentication.
- Only adds new barcodes (skips duplicates).
- Enhanced image preprocessing for better OCR.

---

### POST /photos/api/add-barcode/{card_id}/

Manually add a barcode to a product card.

**Purpose:** Add a barcode that couldn't be auto-detected.

**Request Parameters:**

Path:
- `card_id` (integer, required): Product card ID.

Body (JSON):
- `barcode` (string, required): Barcode value.
- `symbology` (string, optional): Barcode type (default: "EAN13").

**Request Example:**

```bash
curl -X POST http://localhost:8000/photos/api/add-barcode/5/ \
  -H "Content-Type: application/json" \
  -d '{
    "barcode": "1234567890123",
    "symbology": "EAN13"
  }'
```

**Response Format:**

Success (200):
```json
{
  "success": true,
  "message": "Баркод добавлен"
}
```

Error (400):
```json
{
  "success": false,
  "error": "Такой баркод уже существует"
}
```

**Notes:**
- Barcode is added to the first photo of the card.
- Source is set to "manual".
- Prevents duplicate barcodes.
- CSRF exempt.

---

## Admin & Webhooks

### GET /photos/card/{card_id}/

Product card detail page.

**Purpose:** Display and edit product card details with AI suggestions.

**Request Parameters:**

Path:
- `card_id` (integer, required): Product card ID.

**Response:** HTML page

**Notes:**
- Staff member authentication required.
- Displays photos, barcodes, GG labels.
- Auto-fills suggestions using AI if `OPENAI_API_KEY` is set.
- Supports POST for updating card fields.

---

### GET /photos/admin/process-task/{task_id}/

Process a queued external API task.

**Purpose:** Execute a pending processing task (Google Vision, Azure CV, etc.).

**Request Parameters:**

Path:
- `task_id` (integer, required): ProcessingTask ID.

**Response:** Redirect to admin page

**Notes:**
- Staff member authentication required.
- Processes task based on `api_name` field.
- Updates task status and saves results.

---

### POST /photos/api/pochtoy-webhook/

Webhook endpoint for Pochtoy service notifications.

**Purpose:** Receive and process webhooks from Pochtoy API.

**Request Parameters:**

Body (JSON): Pochtoy webhook payload (format varies by event type)

**Request Example:**

```bash
curl -X POST http://localhost:8000/photos/api/pochtoy-webhook/ \
  -H "Content-Type: application/json" \
  -d '{
    "event": "product_status_changed",
    "tracking": "GG747",
    "status": "shipped"
  }'
```

**Response Format:**

Success (200):
```json
{
  "success": true,
  "message": "Webhook processed"
}
```

**Notes:**
- CSRF exempt.
- Requires `ADMIN_CHAT_ID` environment variable.
- Sends notification to admin Telegram chat.

---

### DELETE /photos/api/delete-card-by-correlation/{correlation_id}/

Delete a product card by correlation ID.

**Purpose:** Remove a product card, all its photos, files, and optionally return buffer photos to buffer.

**Request Parameters:**

Path:
- `correlation_id` (string, required): Card correlation ID.

**Request Example:**

```bash
curl -X DELETE http://localhost:8000/photos/api/delete-card-by-correlation/abc12345/
```

**Response Format:**

Success (200):
```json
{
  "success": true,
  "correlation_id": "abc12345",
  "photos_deleted": 3,
  "barcodes_deleted": 2,
  "files_deleted": 3,
  "returned_to_buffer": 0
}
```

Error (404):
```json
{
  "error": "Card not found"
}
```

**Notes:**
- Deletes all photos, barcodes, and physical files.
- Attempts to delete from Pochtoy API if integrated.
- Can optionally return buffer photos to buffer (if they came from buffer).
- CSRF exempt.

---

### GET /photos/sorting/

Buffer photo sorting interface.

**Purpose:** Web interface for manually sorting buffer photos into groups.

**Response:** HTML page with photo grid and sorting controls

**Notes:**
- Staff member authentication required.
- Shows all unprocessed buffer photos.
- Allows grouping and sending to bot or Pochtoy.

---

## Data Models

### PhotoBatch (Product Card)

```json
{
  "id": 1,
  "correlation_id": "abc12345",
  "chat_id": 123456789,
  "message_ids": [1001, 1002],
  "uploaded_at": "2025-11-10T12:34:56.789Z",
  "processed_at": "2025-11-10T12:35:10.123Z",
  "status": "processed",
  "title": "Stone Island Sweater",
  "description": "Premium Italian knitwear...",
  "price": "250.00",
  "condition": "used",
  "category": "Clothing",
  "brand": "Stone Island",
  "size": "XL",
  "color": "Black",
  "sku": "SI-001",
  "quantity": 1,
  "ai_summary": "AI-generated product summary..."
}
```

### Photo

```json
{
  "id": 123,
  "batch": 1,
  "file_id": "AgACAgIAAxkBAAI...",
  "message_id": 1001,
  "image": "/media/photos/2025/11/10/abc12345_0.jpg",
  "uploaded_at": "2025-11-10T12:34:56.789Z",
  "is_main": true,
  "order": 0
}
```

### BarcodeResult

```json
{
  "id": 1,
  "photo": 123,
  "symbology": "EAN13",
  "data": "1234567890123",
  "source": "zbar"
}
```

### PhotoBuffer

```json
{
  "id": 42,
  "file_id": "AgACAgIAAxkBAAI...",
  "message_id": 2001,
  "chat_id": 123456789,
  "image": "/media/buffer/2025/11/10/buffer_42.jpg",
  "uploaded_at": "2025-11-10T12:34:56.789Z",
  "gg_label": "GG747",
  "barcode": "",
  "group_id": 1,
  "group_order": 0,
  "processed": false,
  "sent_to_bot": false
}
```

---

## Environment Variables

Required environment variables for full functionality:

```bash
# OpenAI (for AI summaries, vision, and product detection)
OPENAI_API_KEY=sk-...

# Google APIs (for barcode detection and image search)
GOOGLE_VISION_API_KEY=AIza...
GOOGLE_CUSTOM_SEARCH_API_KEY=AIza...
GOOGLE_CUSTOM_SEARCH_ENGINE_ID=...

# FASHN AI (for photo enhancement)
FASHN_API_KEY=...
CLOUDFLARED_URL=https://...

# Admin notifications
ADMIN_CHAT_ID=123456789
```

---

## Error Handling

All endpoints return consistent error format:

```json
{
  "error": "Error message",
  "success": false
}
```

Some endpoints include additional debug information:

```json
{
  "error": "Error message",
  "success": false,
  "traceback": "Full Python traceback..."
}
```

HTTP status codes:
- `200`: Success
- `400`: Bad request (missing/invalid parameters)
- `404`: Resource not found
- `500`: Server error

---

## Authentication

Most endpoints require one of:
- **CSRF exempt**: Designed for external API calls (Telegram bot)
- **Staff member required**: Web interface endpoints requiring Django admin login

Public endpoints (no auth):
- None (all endpoints require either CSRF token or staff login)

---

## Rate Limiting

No rate limiting is currently implemented. External API calls (OpenAI, Google) have their own rate limits.

---

## Changelog

**v1.0** (2025-11-10)
- Initial API documentation
- All endpoints documented
- Added request/response examples
- Added data model schemas
