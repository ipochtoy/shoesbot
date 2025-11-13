# eBay API Integration - Реализация завершена

## ✅ Что сделано

### 1. OAuth 2.0 авторизация
- ✅ Добавлены методы `get_oauth_url()`, `exchange_code_for_token()`, `refresh_access_token()`
- ✅ View для старта OAuth: `/ebay/oauth/start/`
- ✅ View для callback: `/ebay/oauth/callback/`
- ✅ Автосохранение токенов в БД (`EbayToken`)
- ✅ Автоматическое обновление токенов при истечении

### 2. Реальная публикация через eBay Sell API
- ✅ `create_or_update_listing()` - 3-шаговый процесс:
  1. `_create_inventory_item()` - создание товара
  2. `_create_offer()` - создание предложения с ценой
  3. `_publish_offer()` - публикация
- ✅ Передача всех данных: title, description, photos, price, category, item specifics, UPC/EAN
- ✅ Поддержка business policies (payment, shipping, return)

### 3. Управление листингами
- ✅ `end_listing()` - снятие с публикации через `withdrawOffer`
- ✅ `update_price()` - обновление цены через API
- ✅ Сохранение `offer_id` в модели `EbayCandidate`

### 4. Конфигурация
- ✅ Добавлены settings:
  - `EBAY_CLIENT_ID` - OAuth Client ID
  - `EBAY_CLIENT_SECRET` - OAuth Secret
  - `EBAY_REDIRECT_URI` - OAuth callback URL
  - `EBAY_PAYMENT_POLICY_ID`
  - `EBAY_RETURN_POLICY_ID`
  - `EBAY_FULFILLMENT_POLICY_ID`

### 5. Миграции
- ✅ Создана миграция `0003_ebaycandidate_ebay_offer_id`
- ✅ Применена на сервере

---

## 📋 Что нужно настроить (для юзера)

### Шаг 1: Получить eBay API credentials

1. Зайди на https://developer.ebay.com/
2. Создай новый Application (или используй существующий)
3. В настройках приложения:
   - **Application Type**: выбери "Production" (или "Sandbox" для тестов)
   - **Scopes**: включи:
     - `https://api.ebay.com/oauth/api_scope`
     - `https://api.ebay.com/oauth/api_scope/sell.inventory`
     - `https://api.ebay.com/oauth/api_scope/sell.marketing`
     - `https://api.ebay.com/oauth/api_scope/sell.account`
     - `https://api.ebay.com/oauth/api_scope/sell.fulfillment`
   - **OAuth Redirect URLs**: добавь `https://pochtoy.us/ebay/oauth/callback`

4. Скопируй:
   - **Client ID** (App ID)
   - **Client Secret** (Cert ID)

### Шаг 2: Создать Business Policies в eBay Seller Hub

1. Зайди в https://www.ebay.com/sh/ovw (или sandbox: https://sandbox.ebay.com/sh/ovw)
2. Перейди в **Account → Business Policies**
3. Создай:
   - **Payment Policy** (копируй ID)
   - **Return Policy** (копируй ID)
   - **Shipping Policy** (копируй ID)

### Шаг 3: Обновить .env на сервере

```bash
ssh gcp-shoesbot
nano /home/pochtoy/shoesbot/.env
```

Добавь:

```env
# eBay OAuth 2.0
EBAY_CLIENT_ID=твой_client_id
EBAY_CLIENT_SECRET=твой_client_secret
EBAY_REDIRECT_URI=https://pochtoy.us/ebay/oauth/callback
EBAY_SANDBOX=false  # true для sandbox, false для production

# eBay Business Policies
EBAY_PAYMENT_POLICY_ID=твой_payment_policy_id
EBAY_RETURN_POLICY_ID=твой_return_policy_id
EBAY_FULFILLMENT_POLICY_ID=твой_fulfillment_policy_id

# eBay Finding API (уже есть)
EBAY_APP_ID=твой_app_id
```

Сохрани и рестартни Django:

```bash
sudo systemctl restart shoesdjango.service
```

### Шаг 4: Авторизовать аккаунт

1. Открой браузер:
   ```
   https://pochtoy.us/ebay/oauth/start/
   ```

2. Залогинься на eBay и дай разрешения

3. После успеха вернешься на страницу с подтверждением

4. Токен сохранится в БД и будет автообновляться

---

## 🚀 Как использовать

### Вариант 1: Через админку

1. Открой карточку товара: `/admin/photos/photobatch/{id}/`
2. Внизу увидишь блок "eBay Listing"
3. Жми **"Добавить в eBay"** → создастся `EbayCandidate`
4. Жми **"⚙️ Prepare (AI)"** → заполнятся поля (title, price, category, description)
5. Проверь/отредактируй поля
6. Жми **"🚀 Publish to eBay"**

### Вариант 2: Через API

```bash
# 1. Создать candidate
curl -X POST https://pochtoy.us/api/ebay/candidates/bulk-create/ \
  -H "Content-Type: application/json" \
  -d '{"photo_batch_ids": [123, 456]}'

# 2. Подготовить (AI)
curl -X POST https://pochtoy.us/api/ebay/candidates/1/prepare/

# 3. Опубликовать
curl -X POST https://pochtoy.us/api/ebay/candidates/1/publish/

# 4. Обновить цену
curl -X POST https://pochtoy.us/api/ebay/candidates/1/reprice/ \
  -H "Content-Type: application/json" \
  -d '{"new_price": 29.99}'

# 5. Снять с продажи
curl -X POST https://pochtoy.us/api/ebay/candidates/1/end/
```

---

## 🔧 Технические детали

### Архитектура

```
Client (Browser/API)
    ↓
Django Views (views.py)
    ↓
EbayClient (services/client.py) ← OAuth + Sell API
    ↓
eBay API (api.ebay.com)
```

### OAuth Flow

1. User → `/ebay/oauth/start/` → редирект на eBay
2. User авторизуется на eBay
3. eBay → `/ebay/oauth/callback/?code=...`
4. `exchange_code_for_token(code)` → получаем `access_token` + `refresh_token`
5. Сохраняем в `EbayToken` model
6. При истечении токена → автоматический `refresh_access_token()`

### Publish Flow

1. `create_or_update_listing(candidate)`:
   - Получает токен из БД
   - Создает inventory item (PUT `/sell/inventory/v1/inventory_item/{sku}`)
   - Создает offer (POST `/sell/inventory/v1/offer`)
   - Публикует offer (POST `/sell/inventory/v1/offer/{id}/publish`)
   - Возвращает `listing_id` и URL

2. Сохраняет в модели:
   - `ebay_item_id` = listing_id
   - `ebay_offer_id` = offer_id
   - `status` = 'listed'

---

## 📊 Статус

### ✅ Полностью реализовано
- OAuth 2.0 авторизация
- Получение и обновление токенов
- Публикация через Sell API (Inventory + Offer)
- Снятие с продажи
- Обновление цены
- Интеграция с PhotoBatch (фото, баркоды)
- UI в админке

### ⚠️ Требует конфигурации
- Получить eBay Client ID/Secret
- Создать Business Policies
- Обновить .env на сервере
- Авторизовать аккаунт

### 🔜 Опционально (можно доделать потом)
- Автосинхронизация остатков и продаж
- Category autocomplete с реальным API
- Drag&drop для переупорядочивания фото
- Bulk operations для массовой публикации

---

## 🐛 Troubleshooting

### Ошибка: "No access token available"
→ Пройди авторизацию: `/ebay/oauth/start/`

### Ошибка: "unauthorized_client"
→ Проверь `EBAY_CLIENT_ID` и `EBAY_CLIENT_SECRET` в .env

### Ошибка: "Invalid redirect_uri"
→ Добавь `https://pochtoy.us/ebay/oauth/callback` в настройках приложения на developer.ebay.com

### Ошибка: "Missing business policy"
→ Создай policies в Seller Hub и добавь их ID в .env

---

**Готово к использованию!** Осталось только получить credentials и настроить .env.

