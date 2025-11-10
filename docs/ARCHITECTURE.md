# Architecture Documentation

Подробная документация по архитектуре ShoesBot.

## 📐 Общая Архитектура

ShoesBot состоит из двух основных компонентов:

1. **Telegram Bot** (`shoesbot/`) - Прием фото, обработка баркодов
2. **Django Web App** (`shoessite/`) - Управление карточками, AI генерация

```mermaid
graph LR
    subgraph "Input Layer"
        USER[User] -->|Photos| TG[Telegram Bot]
        USER -->|Web UI| WEB[Django Views]
    end

    subgraph "Processing Layer"
        TG --> PIPELINE[Barcode Pipeline]
        WEB --> SERVICES[Service Layer]
        PIPELINE --> DB[(SQLite DB)]
        SERVICES --> DB
    end

    subgraph "External APIs"
        SERVICES --> OPENAI[OpenAI API]
        SERVICES --> FASHN[FASHN AI]
        SERVICES --> EBAY[eBay API]
    end

    style USER fill:#e1f5ff
    style DB fill:#ffe1e1
    style OPENAI fill:#fff4e1
    style FASHN fill:#fff4e1
    style EBAY fill:#fff4e1
```

## 🤖 Telegram Bot Architecture

### Компоненты

```mermaid
graph TB
    subgraph "telegram_bot.py"
        MAIN[Main Handler]
        BUFFER[Photo Buffer<br/>3s timeout]
        SENDER[MessageSender]
    end

    subgraph "config.py"
        CONFIG[Configuration<br/>All Constants]
    end

    subgraph "helpers.py"
        RETRY[retry_async]
        DOWNLOAD[download_telegram_photo]
        CLEANUP[cleanup_old_entries]
    end

    subgraph "pipeline.py"
        PIPELINE[Barcode Detection<br/>Pipeline]
    end

    subgraph "decoders/"
        ZBAR[ZBarDecoder]
        CV[CV QR Decoder]
        GG[GG Label Decoder]
        OPENAI_DEC[OpenAI Decoder]
    end

    MAIN --> BUFFER
    MAIN --> SENDER
    MAIN --> CONFIG
    MAIN --> RETRY
    BUFFER --> PIPELINE
    PIPELINE --> ZBAR
    PIPELINE --> CV
    PIPELINE --> GG
    PIPELINE --> OPENAI_DEC
```

### Workflow

1. **Photo Reception**: User sends photos to bot
2. **Buffering**: Photos buffered for 3 seconds (await more photos)
3. **Barcode Detection**: Multi-decoder pipeline
4. **API Call**: POST to Django `/api/upload-batch/`
5. **Memory Cleanup**: Background task removes old entries every hour

### Configuration (`config.py`)

```python
@dataclass
class BotConfig:
    BUFFER_TIMEOUT: Final[float] = 3.0
    BUFFER_WAIT_TIME: Final[float] = 3.2
    MAX_RETRIES: Final[int] = 3
    RETRY_DELAYS: Final[tuple] = (0.5, 1.0, 2.0)
    PENDING_TTL_HOURS: Final[int] = 24
    SENT_BATCHES_TTL_HOURS: Final[int] = 48
```

### Barcode Pipeline

```mermaid
graph LR
    IMG[Image] --> FAST[Fast Decoders<br/>ZBar, CV QR]
    FAST -->|No codes| SLOW[Slow Decoders<br/>GG Label]
    SLOW -->|Still no codes| EMERGENCY[Emergency<br/>OpenAI Vision]
    FAST -->|Codes found| RESULT[Results]
    SLOW -->|Codes found| RESULT
    EMERGENCY --> RESULT
```

**Decoder Priority:**
1. **Fast**: ZBar (0.1-0.5s) - 13 types of barcodes
2. **Fast**: CV QR (0.1-0.3s) - QR codes
3. **Slow**: GG Label Improved (1-2s) - Yellow GG+Q labels
4. **Emergency**: OpenAI Vision (3-5s) - When all else fails

### GG+Q Label Detection Logic

```python
# Специальная логика для желтых лейблов
has_gg_text = len(gg_from_ocr) > 0  # "GG" текст найден?
has_q_code = len(gg_from_q) > 0      # Q баркод найден?
has_complete_pair = has_gg_text and has_q_code

if not has_complete_pair:
    # Запускаем emergency OpenAI если неполная пара
    logger.warning(f"Incomplete GG label pair detected")
```

## 🌐 Django Web Application

### Layered Architecture

```mermaid
graph TB
    subgraph "Presentation Layer"
        URLS[urls.py]
        VIEWS[views/]
        TEMPLATES[Templates]
    end

    subgraph "Business Logic Layer"
        SERVICES[services/]
        UTILS[utils/]
    end

    subgraph "Data Access Layer"
        MODELS[models.py]
        DB[(SQLite)]
    end

    subgraph "Middleware Layer"
        REQ_LOG[Request Logging]
        PERF[Performance Monitoring]
        ERR[Error Handling]
    end

    URLS --> VIEWS
    VIEWS --> SERVICES
    VIEWS --> UTILS
    SERVICES --> MODELS
    MODELS --> DB
    REQ_LOG -.->|Wraps| VIEWS
    PERF -.->|Wraps| VIEWS
    ERR -.->|Wraps| VIEWS
```

### Views Module Structure

**Before Refactoring**: `views.py` - 2758 lines

**After Refactoring**: 10 focused modules

```mermaid
graph TB
    INIT[__init__.py<br/>Re-exports all functions]

    UPLOAD[upload.py<br/>315 lines<br/>Upload endpoints]
    PHOTOS[photos.py<br/>189 lines<br/>Photo management]
    AI[ai.py<br/>176 lines<br/>AI generation]
    SEARCH[search.py<br/>775 lines<br/>eBay search]
    BARCODES[barcodes.py<br/>449 lines<br/>Barcode operations]
    ADMIN[admin.py<br/>201 lines<br/>Admin tasks]
    BUFFER[buffer.py<br/>376 lines<br/>Buffer management]
    WEBHOOK[webhook.py<br/>35 lines<br/>Pochtoy webhook]
    ENHANCE[enhance.py<br/>206 lines<br/>FASHN enhancement]

    INIT --> UPLOAD
    INIT --> PHOTOS
    INIT --> AI
    INIT --> SEARCH
    INIT --> BARCODES
    INIT --> ADMIN
    INIT --> BUFFER
    INIT --> WEBHOOK
    INIT --> ENHANCE
```

**Backward Compatibility**: All imports from `photos.views` still work!

```python
# Old code still works:
from photos.views import upload_batch, rotate_photo

# Internally, __init__.py re-exports:
from .upload import upload_batch
from .photos import rotate_photo
```

### Service Layer

Централизованный слой для всех внешних API интеграций.

```mermaid
classDiagram
    class BaseAPIClient {
        +base_url: str
        +timeout: int
        +max_retries: int
        +session: Session
        +get(endpoint, params)
        +post(endpoint, data)
        +_retry_request()
        +_log_request()
    }

    class OpenAIService {
        +api_key: str
        +model: str
        +generate_product_summary()
        +analyze_image()
        +_create_message_content()
    }

    class FASHNService {
        +api_key: str
        +generate_model_with_product()
        +change_background()
        +_poll_prediction_status()
    }

    class SearchService {
        +ebay_app_id: str
        +search_ebay()
        +_parse_ebay_results()
    }

    class ImageService {
        +download_image_from_url()
        +resize_image()
        +convert_to_rgb()
    }

    BaseAPIClient <|-- OpenAIService
    BaseAPIClient <|-- FASHNService
    BaseAPIClient <|-- SearchService
```

**Benefits:**
- ✅ DRY principle - no duplicate HTTP code
- ✅ Unified retry logic with exponential backoff
- ✅ Consistent error handling
- ✅ Type hints + docstrings
- ✅ Easy to test and mock

### Middleware Pipeline

```mermaid
sequenceDiagram
    participant Request
    participant ReqLog as RequestLoggingMiddleware
    participant Perf as PerformanceMiddleware
    participant View as Django View
    participant ErrHandle as ErrorHandlingMiddleware
    participant Response

    Request->>ReqLog: Incoming HTTP request
    ReqLog->>ReqLog: Log request details
    ReqLog->>Perf: Start timer
    Perf->>View: Execute view
    View-->>Perf: Return response / Exception
    alt Exception occurred
        Perf->>ErrHandle: Handle exception
        ErrHandle->>ErrHandle: Log + Create JSON error
        ErrHandle-->>Response: Return error response
    else Success
        Perf->>Perf: Check duration
        alt Duration > 5s
            Perf->>Perf: Log ERROR
        else Duration > 2s
            Perf->>Perf: Log WARNING
        end
        Perf-->>Response: Return response
    end
```

**Middleware Order in `settings.py`:**

```python
MIDDLEWARE = [
    # ... Django built-in middleware ...
    'photos.middleware.request_logging.RequestLoggingMiddleware',  # 1. Log request
    'photos.middleware.performance.PerformanceMonitoringMiddleware',  # 2. Start timer
    'photos.middleware.error_handling.ErrorHandlingMiddleware',  # 3. Catch errors
]
```

### Error Handling Flow

```mermaid
graph TB
    VIEW[View Function] -->|Exception| MIDDLEWARE{ErrorHandlingMiddleware}
    VIEW -->|No Exception| SUCCESS[Return Response]

    MIDDLEWARE -->|ValueError| ERR400[400 Bad Request]
    MIDDLEWARE -->|ValidationError| ERR400
    MIDDLEWARE -->|Http404| ERR404[404 Not Found]
    MIDDLEWARE -->|PermissionDenied| ERR403[403 Forbidden]
    MIDDLEWARE -->|Other Exception| ERR500[500 Server Error]

    ERR400 --> LOG[Log to errors.log]
    ERR404 --> LOG
    ERR403 --> LOG
    ERR500 --> LOG

    LOG --> JSON[Return JSON Response]
```

**Error Response Format:**

```json
{
    "success": false,
    "error": "Error type",
    "details": "Detailed error message"
}
```

### Data Models

```mermaid
erDiagram
    PhotoBatch ||--o{ Photo : contains
    PhotoBatch ||--o{ BarcodeResult : has
    Photo ||--o{ BarcodeResult : has
    Photo ||--o{ PhotoBuffer : temporary

    PhotoBatch {
        int id PK
        string correlation_id UK
        string chat_id
        json message_ids
        string status
        datetime created_at
        datetime processed_at
    }

    Photo {
        int id PK
        int batch_id FK
        file image
        boolean is_main
        int order
        datetime uploaded_at
    }

    BarcodeResult {
        int id PK
        int batch_id FK
        int photo_id FK
        string symbology
        string data
        string source
        datetime detected_at
    }

    PhotoBuffer {
        int id PK
        string correlation_id
        string chat_id
        json message_ids
        json photos_data
        json barcodes
        string status
        datetime created_at
        datetime processed_at
    }
```

## 🎨 Frontend Architecture

### Alpine.js + Modular JS

```mermaid
graph TB
    HTML[product_card.html] --> ALPINE[Alpine.js 3.x<br/>Reactive State]
    HTML --> API_JS[api.js<br/>Axios HTTP calls]
    HTML --> UI_JS[ui.js<br/>Toast notifications]
    HTML --> PHOTO_JS[photo-card.js<br/>Card logic]

    ALPINE -.->|x-data| STATE[Component State]
    API_JS -->|API.method| AXIOS[Axios Instance]
    UI_JS -->|UI.showToast| TOAST[Toast UI]
    PHOTO_JS -->|PhotoCard.action| ALPINE
```

**Files:**
- `api.js` (277 lines) - 15+ API methods with Axios
- `ui.js` (389 lines) - UI utilities, toast notifications
- `photo-card.js` (660 lines) - Card-specific logic

**Before**: ~600 lines inline in template

**After**: Modular, reusable, testable

## 🔐 Security Considerations

### API Keys
- ✅ All keys in environment variables
- ❌ No hardcoded secrets
- ✅ `.env` файл в `.gitignore`

### CSRF Protection
- ✅ Django CSRF middleware enabled
- ✅ `@csrf_exempt` only for API endpoints used by bot
- ✅ Web forms protected with `{% csrf_token %}`

### Input Validation
- ✅ Django form validation
- ✅ Type hints for strong typing
- ✅ Validation in service layer

### Error Handling
- ✅ No traceback in production (unless DEBUG=True)
- ✅ Errors logged to files
- ✅ Generic error messages to users

## 📊 Performance Optimization

### Caching Strategy
- **Current**: No caching (small scale)
- **Future**: Redis for:
  - eBay search results (1 hour)
  - AI-generated summaries (permanent)
  - Session data

### Database Optimization
- ✅ Indexes on: `correlation_id`, `chat_id`, `status`
- ✅ Batch operations where possible
- ✅ `select_related()` for foreign keys

### Image Optimization
- ✅ JPEG compression (quality=90)
- ✅ Resize large images (ImageService)
- ✅ Delete old files on rotation

### API Rate Limiting
- **OpenAI**: 10,000 RPM (tier 1)
- **FASHN**: ~100 requests/day (free tier)
- **eBay**: 5,000 calls/day (standard)

**Strategy**: Background task queue for heavy operations (future)

## 🧪 Testing Strategy

### Unit Tests (Future)
- Service layer (API clients)
- Helper functions
- Decoders

### Integration Tests (Future)
- API endpoints
- Barcode pipeline
- Full workflow

### Manual Testing Checklist
1. ✅ Upload photo via Telegram
2. ✅ Barcode detection works
3. ✅ Create product card in web UI
4. ✅ Generate AI summary
5. ✅ Search eBay
6. ✅ Enhance photo with FASHN
7. ✅ Rotate/delete photos
8. ✅ Export to Pochtoy

## 🚀 Deployment Architecture

### Development
```
├── SQLite database
├── Django runserver
├── Telegram bot (python telegram_bot.py)
└── Local file storage
```

### Production (Recommended)
```mermaid
graph TB
    NGINX[Nginx<br/>Reverse Proxy] --> GUNICORN[Gunicorn<br/>Django WSGI]
    NGINX --> STATIC[Static Files<br/>Nginx direct]
    GUNICORN --> POSTGRES[(PostgreSQL<br/>Database)]
    BOT[Telegram Bot<br/>systemd service] --> GUNICORN
    GUNICORN --> S3[S3 / Object Storage<br/>Media files]

    style NGINX fill:#e1f5ff
    style POSTGRES fill:#ffe1e1
    style S3 fill:#e1ffe1
```

**Production Checklist:**
- [ ] PostgreSQL instead of SQLite
- [ ] Gunicorn/uWSGI for Django
- [ ] Nginx for static files + reverse proxy
- [ ] systemd service for bot
- [ ] S3 for media storage
- [ ] Environment variables via systemd
- [ ] SSL/TLS certificates
- [ ] Log rotation configured
- [ ] Backup strategy

## 📈 Scalability Considerations

### Current Limitations
- Single bot instance
- Single Django instance
- SQLite database
- Local file storage

### Horizontal Scaling (Future)
```mermaid
graph TB
    LB[Load Balancer] --> DJANGO1[Django Instance 1]
    LB --> DJANGO2[Django Instance 2]
    LB --> DJANGO3[Django Instance 3]

    DJANGO1 --> REDIS[(Redis Cache)]
    DJANGO2 --> REDIS
    DJANGO3 --> REDIS

    DJANGO1 --> POSTGRES[(PostgreSQL)]
    DJANGO2 --> POSTGRES
    DJANGO3 --> POSTGRES

    DJANGO1 --> CELERY[Celery Workers<br/>Background Tasks]
    DJANGO2 --> CELERY
    DJANGO3 --> CELERY
```

**When to Scale:**
- More than 1000 users
- More than 100 concurrent requests
- Heavy AI processing load

## 🔍 Monitoring & Observability

### Current Implementation
- ✅ Structured logging (3 files)
- ✅ Performance monitoring (slow requests)
- ✅ Error tracking (exceptions logged)
- ✅ Request logging

### Future Improvements
- [ ] **Prometheus** metrics
- [ ] **Grafana** dashboards
- [ ] **Sentry** error tracking
- [ ] **APM** (Application Performance Monitoring)

### Key Metrics to Track
1. **Request rate** (requests/second)
2. **Response time** (p50, p95, p99)
3. **Error rate** (errors/total requests)
4. **AI API success rate**
5. **Bot uptime**
6. **Database query time**

## 📚 Further Reading

- [Django Best Practices](https://docs.djangoproject.com/en/4.2/)
- [python-telegram-bot Documentation](https://docs.python-telegram-bot.org/)
- [Alpine.js Guide](https://alpinejs.dev/)
- [OpenAI API Documentation](https://platform.openai.com/docs/)
- [FASHN AI Documentation](https://docs.fashn.ai/)

---

**Last Updated**: January 2025
**Version**: 2.0 (Post-Refactoring)
