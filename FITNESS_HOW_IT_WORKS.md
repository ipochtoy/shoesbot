# Как работает сбор данных

## Процесс пошагово

### 1. Когда вызывается сбор данных

**Вариант А: Ручной запрос**
```
Пользователь → Telegram → /report → fitness_reporter.get_daily_report()
```

**Вариант Б: Автоматически каждый день в 21:00**
```
Планировщик → daily_fitness_scheduler → fitness_reporter.get_daily_report()
```

### 2. Что происходит внутри `get_daily_report()`

```python
# 1. Получаем тренировки из TrainingPeaks
workouts = tp_client.get_workouts(start_date=сегодня, end_date=сегодня)
# Делает HTTP запрос: GET https://api.trainingpeaks.com/v1/workouts?startDate=2025-01-15&endDate=2025-01-15
# С заголовком: Authorization: Bearer YOUR_ACCESS_TOKEN

# 2. Получаем питание из MyNetDiary
nutrition = mnd_client.get_today_nutrition()
# Вариант 1: Читает CSV файл (если MYNETDIARY_CSV_PATH установлен)
# Вариант 2: Пытается залогиниться и парсить HTML (если username/password)

# 3. Отправляем данные в ChatGPT
report = chatgpt.generate_report(workouts_data=workouts, nutrition_data=nutrition)
# Делает HTTP запрос: POST https://api.openai.com/v1/chat/completions
# С промптом содержащим тренировки и питание

# 4. Возвращаем готовый отчет
return report
```

## TrainingPeaks - как это работает

### Шаг 1: Получение токенов (один раз)

```python
# 1. Регистрируетесь на https://www.trainingpeaks.com/developer/
# 2. Создаете приложение, получаете CLIENT_ID и CLIENT_SECRET
# 3. Выполняете OAuth авторизацию:

from shoesbot.trainingpeaks_client import TrainingPeaksClient

client = TrainingPeaksClient(
    client_id="ваш_client_id",
    client_secret="ваш_client_secret"
)

# Получаете URL для авторизации
auth_url = client.get_authorization_url("http://localhost:8080/callback")
print(f"Перейдите: {auth_url}")
# Откроется страница TrainingPeaks, вы авторизуетесь

# После авторизации получите code из redirect URL
# Например: http://localhost:8080/callback?code=ABC123

# Обмениваете code на токены
tokens = client.exchange_code_for_tokens("ABC123", "http://localhost:8080/callback")
# Получаете:
# - access_token (действует ~1 час)
# - refresh_token (действует долго, можно обновлять access_token)

# Сохраняете в .env:
# TRAININGPEAKS_ACCESS_TOKEN=...
# TRAININGPEAKS_REFRESH_TOKEN=...
```

### Шаг 2: Ежедневный сбор данных

```python
# Каждый раз когда нужны данные:

# 1. Проверяем токен
if access_token истек:
    обновляем через refresh_token

# 2. Делаем запрос к API
GET https://api.trainingpeaks.com/v1/workouts
  ?startDate=2025-01-15
  &endDate=2025-01-15
Headers:
  Authorization: Bearer YOUR_ACCESS_TOKEN

# 3. Получаем JSON ответ:
[
  {
    "workoutDate": "2025-01-15",
    "workoutType": {"name": "Бег"},
    "duration": 3600,  # секунды
    "distance": 10000  # метры
  },
  {
    "workoutDate": "2025-01-15",
    "workoutType": {"name": "Силовая"},
    "duration": 2700
  }
]
```

## MyNetDiary - как это работает

### Вариант 1: CSV экспорт (РЕКОМЕНДУЕТСЯ)

```python
# 1. Вручную экспортируете данные из MyNetDiary в CSV
# 2. Указываете путь в .env:
MYNETDIARY_CSV_PATH=/path/to/export.csv

# 3. Каждый раз когда нужны данные:
# Читаем CSV файл:
with open('/path/to/export.csv') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['Date'] == '2025-01-15':
            # Собираем данные за нужную дату
            meals.append({
                'meal': row['Meal'],      # "Завтрак"
                'food': row['Food'],       # "Овсянка"
                'calories': row['Calories'] # 300
            })
```

**Формат CSV должен быть:**
```csv
Date,Meal,Food,Calories
2025-01-15,Завтрак,Овсянка,300
2025-01-15,Обед,Курица с рисом,600
2025-01-15,Ужин,Салат,200
```

### Вариант 2: Веб-скрапинг (НЕ РАБОТАЕТ ПОКА)

Текущая реализация - это заглушка. Для реальной работы нужно:
1. Изучить структуру HTML страницы MyNetDiary
2. Использовать BeautifulSoup для парсинга
3. Найти где на странице хранятся данные о питании
4. Извлечь их

**Проблема:** MyNetDiary может менять структуру страницы, нужна постоянная поддержка.

## ChatGPT - как генерируется отчет

```python
# 1. Формируем промпт из данных:

system_prompt = "Ты помощник для анализа тренировок и питания..."

user_prompt = """
Тренировки:
- 2025-01-15: Бег, 1ч 0м, 10.00 км
- 2025-01-15: Силовая, 0ч 45м

Питание:
Калории: 1100 ккал
Завтрак: Овсянка
Обед: Курица с рисом
Ужин: Салат

Создай краткий мотивирующий отчет на русском языке.
"""

# 2. Отправляем в ChatGPT API:
POST https://api.openai.com/v1/chat/completions
{
  "model": "gpt-4o-mini",
  "messages": [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_prompt}
  ]
}

# 3. Получаем ответ:
{
  "choices": [{
    "message": {
      "content": "Отлично! Сегодня ты пробежал 10 км за час..."
    }
  }]
}
```

## Полный пример потока данных

```
┌─────────────────┐
│  Пользователь   │
│  /report        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ telegram_bot.py │
│  report()       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│fitness_reporter │
│get_daily_report │
└────────┬────────┘
         │
         ├─────────────────┬─────────────────┐
         ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│TrainingPeaks │  │  MyNetDiary  │  │   ChatGPT    │
│   API        │  │    CSV/Web   │  │     API      │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       │ HTTP GET        │ Чтение файла    │ HTTP POST
       │ с токеном       │ или парсинг HTML│ с промптом
       │                 │                 │
       ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   JSON       │  │   Dict       │  │   Текст      │
│ тренировки   │  │   питание    │  │   отчет      │
└──────────────┘  └───────────────┘  └──────┬───────┘
                                            │
                                            ▼
                                    ┌──────────────┐
                                    │  Telegram    │
                                    │  сообщение   │
                                    └──────────────┘
```

## Что нужно настроить для работы

### Минимум (только ChatGPT отчеты без данных):
```bash
OPENAI_API_KEY=sk-...
FITNESS_REPORT_CHAT_ID=123456789
```

### С TrainingPeaks:
```bash
# + токены из OAuth авторизации
TRAININGPEAKS_CLIENT_ID=...
TRAININGPEAKS_CLIENT_SECRET=...
TRAININGPEAKS_ACCESS_TOKEN=...
TRAININGPEAKS_REFRESH_TOKEN=...
```

### С MyNetDiary:
```bash
# Вариант 1: CSV (проще)
MYNETDIARY_CSV_PATH=/path/to/export.csv

# Вариант 2: Веб (нужна доработка)
MYNETDIARY_USERNAME=...
MYNETDIARY_PASSWORD=...
```

## Проблемы и решения

**Q: TrainingPeaks токен истек?**
A: Автоматически обновляется через refresh_token

**Q: MyNetDiary CSV не обновляется?**
A: Нужно вручную экспортировать новый CSV или настроить автоматический экспорт

**Q: ChatGPT не генерирует отчет?**
A: Проверьте OPENAI_API_KEY и баланс на аккаунте OpenAI

**Q: Данные не собираются?**
A: Проверьте логи - там будет видно что именно не работает

