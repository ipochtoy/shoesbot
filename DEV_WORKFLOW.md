# eBay Dev Workflow Cheatsheet

Последнее обновление: 13 Nov 2025

## Службы и логи
- Основной Django (бот + eBay): `sudo systemctl restart shoesdjango.service`
- Логи: `tail -f /home/pochtoy/shoesbot/django.log`
- Снапшот media: `~/shoesbot/backup_media.sh` (cron `0 3 * * *`)

Бэкапы медиа уходят в `/home/pochtoy/backups/media/media-YYYYMMDD`. Не запускай `scripts/danger/clean_for_new_user.sh` — он теперь требует `yes`, но лучше вообще не трогать.

## Тестовые данные
- Завели тех. карточку `EBAYTEST001` → candidate `#2`
- Фото: `https://pochtoy.us/media/photos/2025/11/13/ebay_test_photo.jpg`
- Баркод: `123456789012`

Если нужно пересоздать:
```bash
ssh gcp-shoesbot
cd /home/pochtoy/shoesbot/shoessite
python3 manage.py shell < scripts/create_test_candidate.py  # (см. выше код)
```

## Проверка eBay Analyze Flow
1. Вход: `https://pochtoy.us/admin/` (admin / admin123).
2. Анализ: `https://pochtoy.us/ebay/candidates/2/analyze/`
   - `🤖 OpenAI Analysis` может падать (400) на синтетическом 1×1 фото — фиксится реальной картинкой.
   - `🔍 Google Analysis` выдаёт структуру (category_id, condition, UPC).
   - `🛒 Search eBay` теперь работает (после фикса URL) и логирует стратегии даже при 0 попаданий.
   - Новая кнопка `✨ Auto-fill Listing` вызывается прямо с UI (JS дублирует, если шаблон не прогрелся).
   - `autofill` API сохраняет снапшоты в `candidate.analysis_data.ebay_comps_latest / ebay_stock_photos_latest`.
3. Проверка статуса:
   - `autofill-preview` показывает карточку даже без цены (— вместо `$0`).
   - `Continue to Edit Page` активируется после `Use This Data` или Auto-fill.

## Проверка edit-страницы
1. `https://pochtoy.us/ebay/candidates/2/edit/`
   - Сессия подтягивает баннер `✨ Auto-fill applied`, даже если price нет.
   - Поля title/description/category подтягиваются из snapshot.
   - На Pricing Assistant нет цены, т.к. comps пустые — нормальная деградация.

## API ручки для спота-чека
```bash
# eBay search без UI
curl -s -X POST https://pochtoy.us/api/ebay/search/ \
  -H "Content-Type: application/json" \
  -d '{"candidate_id":2,"query":"Test UPC 123456789012"}'

# Auto-fill payload
curl -s -X POST https://pochtoy.us/api/ebay/candidates/2/autofill/ \
  -H "Content-Type: application/json"
```
Ожидаем пустые `comps/stock_photos` + заполненные `analysis_keywords`/`strategies`. При rate-limit eBay Finding API падает на fallback (`EbayClient._scrape_ebay_search`).

## Граничные кейсы
- **OpenAI Vision**: 1×1 image → `image_parse_error`. Используйте реальные фото.
- **eBay API**: частый `Security.RateLimiter (10001)` → срабатывает веб-скрейпинг fallback и всё равно сохраняет стратегию.
- **Auto-fill Preview**: раньше падало на `null.toFixed()` — исправлено.

## Чеклист перед выкладкой
1. `sudo systemctl restart shoesdjango.service` (убедиться, что поднялся).
2. `https://pochtoy.us/ebay/candidates/2/analyze/`:
   - Google анализ выдаёт структуру.
   - `Search eBay` → статус `Готово: ничего не найдено` (или список).
   - `Auto-fill Listing` → отображает превью, без JS-ошибок.
3. `https://pochtoy.us/ebay/candidates/2/edit/` → зелёный баннер + sessionStorage очистился.
4. `~/shoesbot/scripts/dev_health.sh` → оба эндпоинта 200.
5. `~/shoesbot/backup_media.sh` (или cron лог) — бэкап жив.

### Если нужен свежий тест
- Перегенерируй фото (не 1×1).
- Очисти старые снапшоты:
  ```bash
  python3 manage.py shell
  >>> from apps.marketplaces.ebay.models import EbayCandidate
  >>> cand = EbayCandidate.objects.get(id=2)
  >>> cand.analysis_data = {}
  >>> cand.save(update_fields=['analysis_data'])
  ```
- Повтори анализ.
