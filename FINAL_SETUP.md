# Dev окружение готово!

## Что сделано

✅ Dev Django запущен на порту 8001  
✅ Dev БД создана (копия production)  
✅ Production не затронут (порт 8000 работает)  
✅ Скрипты для управления готовы  

## Настройка nginx (один раз, нужен sudo)

```bash
ssh gcp-shoesbot
cd ~/shoesbot
sudo ./setup_nginx_dev.sh
```

После этого будет доступ: **https://pochtoy.us:8001**

## Доступ сейчас

**Локально на сервере:**
- Dev: http://127.0.0.1:8001/admin/
- Production: http://127.0.0.1:8000/admin/ (не трогать!)

**После настройки nginx:**
- Dev: https://pochtoy.us:8001/admin/
- Production: https://pochtoy.us/admin/ (не трогать!)

## Управление

**Запуск dev:**
```bash
ssh gcp-shoesbot
cd ~/shoesbot
./run_dev_django.sh
```

**Обновление dev БД из production:**
```bash
./sync_dev_db.sh
```

## Важно

- Production (8000) - бот и склад, НЕ ТРОГАТЬ
- Dev (8001) - можно крашить/перезапускать сколько угодно
- Dev БД изолирована от production

