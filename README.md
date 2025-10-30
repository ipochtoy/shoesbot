# Shoestest Bot

Telegram бот для извлечения штрихкодов и QR-кодов из фотографий.

## Архитектура

- **Модульная структура**: `shoesbot/` - пакет с плагинами декодеров
- **Pipeline**: последовательная обработка несколькими декодерами (zbar, opencv-qr, vision-ocr)
- **Рендеринг**: Jinja2-шаблоны для стабильных карточек товаров
- **Метрики**: JSONL лог с таймингом каждого декодера
- **Admin notifications**: автоотчёты при фейлах

## Установка

```bash
# Системные зависимости
brew install zbar

# Python окружение
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

# Токен бота
echo "BOT_TOKEN=your_token_here" > .env
```

## Запуск

```bash
# macOS: DYLD_LIBRARY_PATH нужен для pyzbar
DYLD_LIBRARY_PATH=/opt/homebrew/lib .venv/bin/python -u bot.py

# Или через nohup:
DYLD_LIBRARY_PATH=/opt/homebrew/lib nohup .venv/bin/python -u bot.py > bot.log 2>&1 &
```

## Команды бота

- `/start` - старт
- `/ping` - проверка
- `/debug_on` - подробные логи + сохранение образцов в `data/samples/`
- `/debug_off` - обычные логи
- `/diag` - инфо о системе (версии библиотек)
- `/admin_on` - включить уведомления админу при фейлах
- `/stats` - статистика по последним ~500 фото

## Структура

```
shoesbot/
├── decoders/          # Плагины декодеров (zbar, opencv-qr, vision-ocr)
├── renderers/         # Рендеринг карточек (Jinja2)
├── models.py          # Barcode dataclass
├── pipeline.py        # DecoderPipeline для последовательной обработки
└── telegram_bot.py    # Обработчики Telegram
data/
├── metrics.jsonl      # JSONL лог с метриками
├── admin.json         # ID админа
└── samples/           # Образцы фото (при debug_on)
```

## Добавление нового декодера

```python
# shoesbot/decoders/my_decoder.py
from shoesbot.decoders.base import Decoder
from shoesbot.models import Barcode
from typing import List
from PIL import Image

class MyDecoder(Decoder):
    name = "my-decoder"

    def decode(self, image: Image.Image, image_bytes: bytes) -> List[Barcode]:
        # твоя логика
        return [Barcode(symbology="TYPE", data="value", source=self.name)]
```

Зарегистрируй в `telegram_bot.py`:
```python
pipeline = DecoderPipeline([ZBarDecoder(), OpenCvQrDecoder(), VisionDecoder(), MyDecoder()])
```

## Known Issues

- zbar на macOS требует `DYLD_LIBRARY_PATH=/opt/homebrew/lib`
- Vision OCR работает только при установленном `GOOGLE_APPLICATION_CREDENTIALS`

