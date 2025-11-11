# Workflow работы с проектом

## ✅ Что настроено

- **Домен:** https://pochtoy.us/admin/
- **HTTPS:** Let's Encrypt (автообновление)
- **Git деплой:** Автоматический
- **Сервисы:** Перезапуск без пароля
- **Админка Django:** Работает с CSS

## 🚀 Деплой изменений (одна команда)

В Cursor просто запусти:

```bash
./deploy_from_local.sh
```

Или через меню: `Cmd+Shift+P` → `Tasks: Run Task` → `🚀 Deploy to VM`

Скрипт автоматически:
1. Коммитит изменения
2. Пушит в GitHub
3. На VM: git pull
4. Собирает статику
5. Перезапускает сервисы

**ВСЁ!** Никаких ручных действий.

## 📊 Полезные команды

`Cmd+Shift+P` → `Tasks: Run Task`:

- **📊 VM Status** — статус бота и Django
- **📋 Bot Logs** — логи бота в реальном времени
- **📋 Django Logs** — логи Django
- **🔄 Restart Services** — перезапустить сервисы

## 🔗 Полезные ссылки

- Админка: https://pochtoy.us/admin/
- Страница сортировки: https://pochtoy.us/photos/
- GitHub: https://github.com/ipochtoy/shoesbot

## 🛠️ Если что-то сломалось

### Проверить статус сервисов

```bash
ssh gcp-shoesbot
sudo systemctl status shoesbot.service
sudo systemctl status shoesdjango.service
```

### Посмотреть логи

```bash
ssh gcp-shoesbot
tail -f ~/shoesbot/bot.log
tail -f ~/shoesbot/django.log
```

### Перезапустить всё

```bash
ssh gcp-shoesbot
sudo systemctl restart shoesbot.service
sudo systemctl restart shoesdjango.service
sudo systemctl restart nginx
```

### Откатить изменения

```bash
ssh gcp-shoesbot
cd ~/shoesbot
git log  # Найди нужный коммит
git reset --hard COMMIT_ID
./deploy.sh
```

---

**Теперь работай спокойно — всё автоматизировано!** 🎉

