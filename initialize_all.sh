#!/bin/bash
# Мастер-скрипт для полной инициализации системы
set -e

echo "════════════════════════════════════════════"
echo "  ИНИЦИАЛИЗАЦИЯ SHOESBOT PRODUCTION"
echo "════════════════════════════════════════════"
echo ""

read -p "Запустить полную инициализацию? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Отменено"
    exit 0
fi

echo ""
echo "1. Критический бекап..."
./critical_backup.sh

echo ""
echo "2. Фиксация текущего состояния в Git..."
./git_commit_stable.sh

echo ""
echo "3. Исправление production settings..."
./fix_settings_production.sh

echo ""
echo "4. Настройка DEV окружения..."
./setup_dev_environment.sh
./install_dev_service.sh

echo ""
echo "5. Отключение rsync deployment..."
./disable_rsync_deploy.sh

echo ""
echo "6. Настройка автоматических бекапов..."
./setup_cron_backup.sh

echo ""
echo "7. Установка watchdog..."
./install_watchdog.sh

echo ""
echo "8. Установка git hooks..."
./install_git_hooks.sh

echo ""
echo "9. Перезапуск Django..."
./restart_django.sh

echo ""
echo "════════════════════════════════════════════"
echo "  ✅ ИНИЦИАЛИЗАЦИЯ ЗАВЕРШЕНА"
echo "════════════════════════════════════════════"
echo ""
echo "Запускаю полную проверку системы..."
./full_check.sh

echo ""
echo "Все готово! Следующие шаги:"
echo "  1. Проверь админку: https://pochtoy.us/admin/"
echo "  2. Проверь бота в Telegram"
echo "  3. Прочитай ОПЕРАЦИИ.md для дальнейшей работы"
