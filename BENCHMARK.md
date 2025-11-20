## Benchmarking бот-обработчика

Скрипт `tools/benchmark_bot.py` позволяет прогонять синтетический пакет фото
через `process_photo_batch` без Telegram/Django (включается `BENCHMARK_MODE=1`),
сохранять результаты в JSON и сравнивать их между коммитами.

### Как снять метрики

```bash
# 1. Сгенерировать 6 тестовых изображений и выполнить 3 прогона
python tools/benchmark_bot.py --generate 6 --iterations 3 --output bench-current.json --label HEAD

# 2. Для «старой» версии создать worktree и запустить там же
git worktree add /tmp/shoesbot-old <old-commit>
cd /tmp/shoesbot-old
python tools/benchmark_bot.py --generate 6 --iterations 3 --output bench-old.json --label baseline
```

JSON содержит среднее время, стандартное отклонение, минимальное/максимальное
значение и флаг `openai_used`. Для наглядного сравнения достаточно открыть оба
файла и сопоставить `avg_seconds`.

### Использование собственных фото

```bash
python tools/benchmark_bot.py --images "bench_samples/*.jpg" --iterations 5
```

- Поддерживается несколько шаблонов `--images`.
- Если нужен другой размер synthetic-фото: `--generate 8 --image-size 800x800`.

### Как откатиться

После деплоя фиксирующий коммит можно получить командой:

```bash
git rev-parse HEAD
```

Для быстрого отката:

```bash
git reset --hard <saved-commit>
```

