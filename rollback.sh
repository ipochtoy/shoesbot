#!/bin/bash
# Rollback script - откат к версии до рефакторинга

set -e

echo "🔄 ShoesBot Rollback Script"
echo "==========================="
echo ""
echo "Этот скрипт откатит все изменения к версии до рефакторинга."
echo ""
echo "Доступные точки отката:"
echo "  1) backup-before-refactoring (tag)"
echo "  2) backup/pre-refactoring-2025-01-10 (branch)"
echo ""

read -p "Вы уверены, что хотите откатить изменения? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Отмена отката"
    exit 0
fi

echo ""
echo "Выберите способ отката:"
echo "  1) Tag (рекомендуется)"
echo "  2) Branch"
echo ""

read -p "Выберите (1 или 2): " choice

if [ "$choice" = "1" ]; then
    echo ""
    echo "🔄 Откат к tag: backup-before-refactoring..."
    git checkout backup-before-refactoring
    echo "✅ Откат выполнен!"
    echo ""
    echo "Текущая версия: до рефакторинга (commit: $(git rev-parse --short HEAD))"
    echo ""
    echo "Чтобы вернуться к отрефакторенной версии:"
    echo "  git checkout claude/project-review-011CUxPJVQzhPacdoVSkuTu2"

elif [ "$choice" = "2" ]; then
    echo ""
    echo "🔄 Откат к branch: backup/pre-refactoring-2025-01-10..."
    git checkout backup/pre-refactoring-2025-01-10
    echo "✅ Откат выполнен!"
    echo ""
    echo "Текущая версия: до рефакторинга (commit: $(git rev-parse --short HEAD))"
    echo ""
    echo "Чтобы вернуться к отрефакторенной версии:"
    echo "  git checkout claude/project-review-011CUxPJVQzhPacdoVSkuTu2"

else
    echo "❌ Неверный выбор"
    exit 1
fi
