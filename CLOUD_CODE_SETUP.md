# Подключение Cloud Code к GCP VM

## 🚀 Быстрый старт (3 шага)

1. **Установи Remote SSH**: `Cmd+Shift+X` → найди "Remote - SSH" → Install
2. **Подключись**: `Cmd+Shift+P` → `Remote-SSH: Connect to Host` → выбери `gcp-shoesbot`
3. **Открой папку**: `Cmd+O` → `/home/pochtoy/shoesbot`

Готово! Теперь работаешь напрямую с кодом на VM.

---

## Автоматическая настройка

### 1. Установи расширение Remote SSH
- Открой Cloud Code
- Перейди в Extensions (`Cmd+Shift+X`)
- Найди и установи: **Remote - SSH**

### 2. Подключись к VM
- Нажми `Cmd+Shift+P`
- Введи: `Remote-SSH: Connect to Host`
- Выбери: `gcp-shoesbot` (или введи `pochtoy@34.45.43.105`)
- Введи пароль если попросит (или используй SSH ключ)

### 3. Открой папку проекта
- После подключения нажми `Cmd+O` или `File → Open Folder`
- Введи путь: `/home/pochtoy/shoesbot`
- Нажми "OK"

### 4. Готово!
Теперь ты работаешь напрямую с кодом на VM. Все изменения сохраняются на сервере.

## Полезные команды

### Через Tasks в Cloud Code (удобнее!)
- `Cmd+Shift+P` → `Tasks: Run Task` → выбери нужную задачу:
  - **Restart Bot** - перезапустить бота
  - **Restart Django** - перезапустить Django
  - **Status Bot** - статус бота
  - **Status Django** - статус Django
  - **Tail Bot Logs** - логи бота в реальном времени
  - **Tail Django Logs** - логи Django в реальном времени

### Или через терминал
```bash
# Проверить статус
sudo systemctl status shoesbot.service
sudo systemctl status shoesdjango.service

# Перезапустить
sudo systemctl restart shoesbot.service
sudo systemctl restart shoesdjango.service

# Логи
tail -f ~/shoesbot/bot.log
tail -f ~/shoesbot/django.log
```

## SSH конфигурация

SSH конфиг уже настроен в `~/.ssh/config`:
```
Host gcp-shoesbot
    HostName 34.45.43.105
    User pochtoy
    IdentityFile ~/.ssh/gcp_vm_key
```

## Troubleshooting

### Если не подключается:
1. Проверь что SSH ключ на месте: `ls -la ~/.ssh/gcp_vm_key`
2. Проверь что ключ добавлен на VM: `ssh gcp-shoesbot 'cat ~/.ssh/authorized_keys | grep cursor'`
3. Если ключа нет на VM, добавь его через веб-консоль Google Cloud

### Если не видит Python окружение:
- Cloud Code должен автоматически найти `.venv` в `/home/pochtoy/shoesbot/.venv`
- Если нет, выбери интерпретатор: `Cmd+Shift+P` → `Python: Select Interpreter` → `/home/pochtoy/shoesbot/.venv/bin/python3`

