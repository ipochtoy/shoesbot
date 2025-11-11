# eBay MVP — Задача для Claude Web

**ВАЖНО**: Ты Senior Django/DRF разработчик. Пиши рабочий код без болтовни. Создай минимально-живую реализацию выставления на eBay.

---

## 📋 ТЗ: Что нужно сделать

### Контекст (жёсткие факты):

- 1 eBay-аккаунт; используем уже настроенные Business Policies (shipping/return/payment)
- Категории разные (парфюм, обувь, одежда, электроника, «барахло»)
- Фото пока хостятся на нашем домене `https://pochtoy.us`
- Идентификация товара: по названию, UPC/EAN/ISBN и визуалу (допускаем листинг без каталог-матча)
- Ценообразование: всегда ниже медианы рынка; free shipping включён в цену
- Нужен сайдбар-помощник цены (компы, медиана, подсказки)
- Один склад, товар может лежать в разных местах; нужно фиксировать факт продажи
- Бюджет GPT — без ограничений (сделай интерфейс провайдера с простыми заглушками)
- Далее планируется Shopify, поэтому сделай абстракции так, чтобы было легко добавить второй паблишер

### Что нужно сделать (MVP за один проход):

**1. Приложение `apps/marketplaces/ebay/` + интеграция в существующий каталог**

**2. Модели (минимум, со штампами времени):**

Используй существующую модель `PhotoBatch` (см. контекст ниже) как основу для товаров.

- `EbayCandidate`: 
  - `photo_batch` (FK to PhotoBatch)
  - `status` {draft, ready, listed, error, ended}
  - `category_id`, `ebay_item_id`, `condition`
  - `specifics` JSON
  - `description_md`
  - `title` (<=80)
  - `price_suggested`, `price_final`
  - `comps` JSON
  - `photos` JSON (упорядоченные URLs)
  - `policies` JSON
  - `logs` JSON
  - `heavy_flag` bool
  - timestamps

- `EbayToken`:
  - `account='default'`
  - `access_token`, `refresh_token`
  - `expires_at`
  - `sandbox` bool
  - timestamps

**3. Админка:**

- В списке `PhotoBatch` добавить mass action «Отправить в eBay» — создаёт `EbayCandidate` со статусом `draft`
- Слева (в админке) — вкладка «eBay» со списком кандидатов:
  - Фильтры по статусу/категории/heavy
  - Действия: «Удалить из списка», «Опубликовать», «Снять», «Обновить цену по медиане»
- В карточке товара (детальной странице `PhotoBatch`) — секция «eBay Listing»:
  - Drag&drop фото (переупорядочивание, выбор главной)
  - Поля: Title, Condition, Category (autocomplete), Item specifics (динамичные обязательные)
  - Description (Markdown)
  - Сайдбар цены: медиана, p25/p75, поле «ниже медианы на X%», чекбокс Best Offer, расчёт `price_final = median*(1−X%) + ship_cost`

**4. API-слой (DRF):**

Эндпоинты `/api/ebay/...`:
- `POST /candidates/bulk-create` {photo_batch_ids: []}
- `GET /candidates` (фильтры status, q по sku/title)
- `POST /candidates/{id}/prepare` — запускает пайплайн подготовки
- `POST /candidates/{id}/publish` / `POST /{id}/end` / `POST /{id}/reprice`
- `GET /taxonomy/suggest?q=...` — поиск категории
- `GET /specifics?category_id=...` — обязательные item specifics
- `GET /pricing/comps?q|upc|ean=...` — компы и медиана

Сериализаторы под `EbayCandidate` и вспомогательные схемы.

**5. Пайплайн подготовки кандидата (service-слой):**

- `gpt_vision_extract(images)` — верни `{brand, model, variant, volume, condition_guess, codes[], key_terms[]}`. **Пока сделай заглушку** с простым извлечением текста и фиктивными полями.
- `taxonomy_suggest()` → категория
- `fetch_required_specifics(category_id)` → список обязательных атрибутов
- `gpt_write_listing(data)` → `{title, condition, specifics{}, bullets[], description_md}` (title <=80 символов)
- `browse_comps(query/codes)` → выбор сопоставимых лотов, расчёт медианы/p25/p75
- `finalize_price(median, ship_cost, X%)` → `price_suggested`, `price_final`. Учесть free shipping
- Присвоить статус `ready` если обязательные specifics заполнены, иначе оставить `draft` и вернуть список недостающих полей

**6. Публикация/обновление:**

- Класс `EbayClient` с методами-заглушками:
  - `create_or_update_listing(candidate)`
  - `upload_media(urls)`
  - `end_listing(item_id)`
  - `get_business_policies()`
  - `get_required_specifics(category_id)`
  - `search_comps(...)`
- Хранить и отображать логи запросов/ответов (даже для заглушек)

**7. Очереди:**

- Celery с очередями `ebay_io`, `pricing`, `gpt`
- Задачи: `prepare`, `publish`, `end`, `reprice` (массово и по одному)

**8. UI (минимально, без тяжёлого фронта):**

- Шаблоны Django или простая HTMX-страница для списка кандидатов и блока в карточке товара
- Drag&drop фото через `<input type="file" multiple>` + сортировка (SortableJS) — только если уже подключен статик; иначе простая форма, но архитектурно поддержи порядок фото

**9. Массовые операции:**

- `bulk_publish`, `bulk_end`, `bulk_reprice`, `bulk_delete_from_list`
- Отчёт об ошибках: показывай только упавшие позиции с причиной

**10. Продажи/остатки:**

- В `PhotoBatch` добавь поле `locations` JSON держим массив `{name, qty}`. При публикации суммарный qty = сумма по локациям
- Добавь простую команду `sync_ebay_sales` (management command), которая уменьшает qty по заказам из `EbayClient.fetch_orders()` (пока заглушка)

---

## 📂 Набор файлов которые НУЖНО сгенерировать:

```
apps/marketplaces/ebay/
├── __init__.py
├── models.py           # EbayCandidate, EbayToken
├── admin.py            # mass action, вкладка «eBay», инлайн секция
├── serializers.py      # DRF serializers
├── views.py            # DRF viewsets/views
├── urls.py             # /api/ebay/* маршруты
├── services/
│   ├── __init__.py
│   ├── pipeline.py     # prepare workflow
│   ├── pricing.py      # comps, median, pricing
│   ├── gpt.py          # vision + writer stubs
│   └── client.py       # EbayClient stub
├── tasks.py            # Celery tasks
├── templates/ebay/
│   ├── candidates_list.html
│   └── partials/
│       └── product_ebay_block.html
└── management/
    └── commands/
        └── sync_ebay_sales.py
```

**Также обнови:**
- `shoessite/shoessite/settings.py` — добавь app в `INSTALLED_APPS`, переменные окружения
- `shoessite/shoessite/urls.py` — подключи `/ebay/` и `/api/ebay/`

---

## 🏗️ Контекст существующего проекта

### Структура проекта:

```
shoesbot/
├── shoessite/              # Django проект
│   ├── shoessite/          # Settings & URLs
│   │   ├── settings.py
│   │   └── urls.py
│   ├── photos/             # Существующее приложение (товары/фото)
│   │   ├── models.py       # PhotoBatch, Photo, BarcodeResult
│   │   ├── admin.py
│   │   ├── views.py
│   │   └── templates/
│   └── manage.py
└── apps/                   # Создай тут новые приложения
    └── marketplaces/
        └── ebay/           # <-- ТУТ ТВОЙ КОД
```

### Существующие модели (photos/models.py):

```python
class PhotoBatch(models.Model):
    """Карточка товара - батч фото загруженных из Telegram бота."""
    correlation_id = models.CharField(max_length=32, unique=True, db_index=True)
    chat_id = models.BigIntegerField(db_index=True)
    message_ids = models.JSONField(default=list)
    uploaded_at = models.DateTimeField(default=timezone.now)
    processed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[...], default='pending')
    
    # Описание товара
    title = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    condition = models.CharField(max_length=50, choices=[...], blank=True)
    category = models.CharField(max_length=200, blank=True)
    brand = models.CharField(max_length=200, blank=True)
    size = models.CharField(max_length=100, blank=True)
    color = models.CharField(max_length=100, blank=True)
    sku = models.CharField(max_length=200, blank=True)
    quantity = models.IntegerField(default=1)
    ai_summary = models.TextField(blank=True)

class Photo(models.Model):
    """Фото из карточки товара."""
    batch = models.ForeignKey(PhotoBatch, related_name='photos', on_delete=models.CASCADE)
    file_id = models.CharField(max_length=255)
    message_id = models.BigIntegerField()
    image = models.ImageField(upload_to='photos/%Y/%m/%d/')
    uploaded_at = models.DateTimeField(default=timezone.now)
    is_main = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

class BarcodeResult(models.Model):
    """Баркод найденный на фото."""
    photo = models.ForeignKey(Photo, related_name='barcodes', on_delete=models.CASCADE)
    symbology = models.CharField(max_length=50)
    data = models.CharField(max_length=500)
    source = models.CharField(max_length=50)  # zbar, opencv-qr, vision-ocr, gg-label
```

### Существующий settings.py (релевантные части):

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'photos',
    # <-- ДОБАВЬ СЮДА 'apps.marketplaces.ebay'
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR.parent / 'static'
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# <-- ДОБАВЬ НОВЫЕ ПЕРЕМЕННЫЕ:
# EBAY_SANDBOX = True
# EBAY_APP_ID = ''
# EBAY_DEV_ID = ''
# EBAY_CERT_ID = ''
# GPT_PROVIDER = 'openai'  # stub for now
# PRICE_BELOW_MEDIAN_PCT = 0.08  # 8%
# DEFAULT_SHIP_COST = 4.99
```

### Существующий urls.py:

```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(url='/photos/sorting/', permanent=False)),
    path('admin/', admin.site.urls),
    path('photos/', include('photos.urls')),
    # <-- ДОБАВЬ:
    # path('ebay/', include('apps.marketplaces.ebay.urls')),
    # path('api/ebay/', include('apps.marketplaces.ebay.urls')),  # или отдельный urls для API
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

### Паттерны admin.py (как делаем):

```python
from django.contrib import admin
from django.utils.html import format_html

@admin.register(PhotoBatch)
class PhotoBatchAdmin(admin.ModelAdmin):
    list_display = ['correlation_id_link', 'product_title', 'status', 'photo_count']
    list_filter = ['status', 'uploaded_at']
    search_fields = ['correlation_id', 'title']
    actions = ['send_to_ebay']  # <-- ТВОЙ MASS ACTION
    
    @admin.action(description='Отправить в eBay')
    def send_to_ebay(self, request, queryset):
        # Создай EbayCandidate для каждого PhotoBatch
        pass
```

---

## 🎯 Критерии приёмки:

✅ В админке у товаров (`PhotoBatch`) появился mass action «Отправить в eBay»
✅ Вкладка «eBay» показывает список кандидатов с фильтрами/поиском и массовыми действиями
✅ В карточке товара видно блок «eBay Listing» с фото, автополя и прайс-сайдбар (пусть даже часть данных — от заглушек)
✅ `POST /api/ebay/candidates/{id}/prepare` заполняет поля и вычисляет цену (ниже медианы + доставка)
✅ `POST /api/ebay/candidates/{id}/publish` меняет статус на `listed` (через мок-клиент), `end` — на `ended`
✅ Логи запросов сохраняются в `EbayCandidate.logs`
✅ Тесты проходят
✅ `python manage.py migrate` успешно отрабатывает

---

## ⚠️ Важно:

- **Пиши аккуратные сериализаторы/валидаторы** для item specifics, проверяй Title ≤80 символов
- **Не завязывайся на реальный eBay сейчас** — клиент и ответы смокай, но спроектируй сигнатуры так, чтобы потом подменить заглушки на реальные вызовы Sell/Browse/Taxonomy
- **Код — PEP8, понятные имена, типы (mypy-friendly), без лишних зависимостей**
- **НЕ ТРОГАЙ БОТ** — весь код только в Django (`shoessite/` и `apps/`)

---

## 📦 Промпты для GPT (готовые заготовки для заглушек):

### Vision-extract (OCR лейблов/кодов)

```
Вход: 1-10 фото товара (лейблы/штрих-коды/коробка).
Задача: извлеки бренд, линейку/модель, объём/размер, состояние, коды (UPC/EAN/ISBN), ключевые фразы.
Если не уверены — UNKNOWN.
Верни JSON: {brand, model, variant, volume, condition_guess, codes:[{type,value}], key_terms[]}.
Не выдумывай.
```

### Listing-writer (title/description/specifics)

```
Вход: JSON c извлечёнными данными, предполагаемая eBay-категория, язык=EN.
Ограничения: title ≤80 символов: Brand + Model + Size/Volume + Condition.
Описание: 2–3 абзаца + 5 буллетов; без гарантий, без запрещённых claims.
Верни JSON: {title, condition, specifics:{...}, bullets:[...], description_md}.
Если атрибут обязателен, а данных нет — пометь REQUIRED_MISSING.
```

### Comps-selector

```
Вход: результаты eBay Browse/Find (цена/состояние/локация/репутация).
Отбери сопоставимые товары, посчитай медиану.
Верни {selected_ids:[...], median, p25, p75}.
```

### Price-finalizer

```
Вход: median/p25/p75, X% снижения, ship_cost.
Верни {price_suggested, rationale}.
```

---

## 🧪 Тесты (tests/test_ebay_pipeline.py):

```python
from django.test import TestCase
from photos.models import PhotoBatch
from apps.marketplaces.ebay.models import EbayCandidate
from apps.marketplaces.ebay.services.pipeline import prepare_candidate

class EbayPipelineTestCase(TestCase):
    def test_prepare_candidate(self):
        # Создаём PhotoBatch
        batch = PhotoBatch.objects.create(
            correlation_id='test123',
            chat_id=123,
            title='Test Product',
        )
        
        # Создаём EbayCandidate
        candidate = EbayCandidate.objects.create(
            photo_batch=batch,
            status='draft',
        )
        
        # Запускаем prepare
        result = prepare_candidate(candidate.id)
        
        # Проверяем
        candidate.refresh_from_db()
        self.assertIn(candidate.status, ['draft', 'ready'])
        self.assertIsNotNone(candidate.price_suggested)
        self.assertTrue(len(candidate.logs) > 0)
```

---

## 🚀 Инструкции для выполнения:

1. **Создай структуру приложения** `apps/marketplaces/ebay/` со всеми файлами
2. **Напиши модели** `EbayCandidate` и `EbayToken` с миграциями
3. **Интегрируй в админку** — mass action, вкладка, инлайн блок
4. **Создай DRF API** — сериализаторы, views, URLs
5. **Реализуй service layer** — pipeline, pricing, gpt stubs, client stubs
6. **Добавь Celery tasks** — prepare, publish, end, reprice
7. **Создай templates** — список кандидатов, блок в карточке
8. **Добавь management command** — sync_ebay_sales
9. **Напиши тесты** — test_ebay_pipeline.py
10. **Обнови settings.py и urls.py**

---

## 📥 КАК ЗАБРАТЬ РЕЗУЛЬТАТ:

После того как Claude Web создаст код:

### 1. Создай файлы в проекте:

Скопируй каждый файл который Claude Web сгенерировал в соответствующее место в проекте.

Например:
- `apps/marketplaces/ebay/models.py` → создай путь и файл
- `apps/marketplaces/ebay/admin.py` → создай файл
- И так далее для всех файлов

### 2. Установи зависимости (если нужны):

Если Claude Web добавил новые зависимости в requirements.txt — установи их:
```bash
pip install -r requirements.txt
```

### 3. Примени миграции:

```bash
cd shoessite
python manage.py makemigrations
python manage.py migrate
```

### 4. Запусти тесты:

```bash
python manage.py test tests.test_ebay_pipeline
```

### 5. Проверь админку:

```bash
python manage.py runserver
# Открой http://localhost:8000/admin/
```

### 6. Если всё ОК — коммит и деплой:

```bash
git add .
git commit -m "Add eBay MVP integration"
./deploy_from_local.sh
```

---

## ✅ Чек-лист перед деплоем:

- [ ] Все файлы созданы
- [ ] Миграции применились без ошибок
- [ ] Тесты проходят
- [ ] В админке появился mass action «Отправить в eBay»
- [ ] Вкладка «eBay» открывается
- [ ] API endpoints отвечают (можно проверить через `/api/ebay/candidates/`)
- [ ] Логи сохраняются в `EbayCandidate.logs`
- [ ] Бот не сломан (не трогали файлы бота)

---

## 🎁 Дополнительные детали для учета:

### Правила цены:

- Считаем медиану по релевантным компам (фильтры: состояние, локация, рейтинг продавца)
- Формула: `target = round_down(median * (1 - X%), step=0.01)`; X% хранится в `settings.PRICE_BELOW_MEDIAN_PCT`
- Free shipping: `price_final = target + ship_cost`
- Поддерживаем Best Offer (опционально) с нижней границей `min_accept = price_final * (1 - Y%)`

### Модерация тяжёлых:

- Флаг `heavy_flag=True` → публикация требует подтверждения в админке
- Шаблоны политик «Heavy» (особые shipping/returns), автоприменение по весу/габаритам/категории

### State machine:

`draft` → `ready` → `listed` → `error` → `ended`

Логи запросов/ответов для поддержки.

---

**НАЧИНАЙ КОДИТЬ! Удачи!** 🚀

