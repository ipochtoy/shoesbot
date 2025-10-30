# Инструкция: запушить shoesbot в GitHub

## Шаг 1: Создай репозиторий
1. Открой https://github.com/new
2. Имя: `shoesbot`
3. Public (или Private)
4. НЕ добавляй README/license/.gitignore (они уже есть)
5. Нажми "Create repository"

## Шаг 2: Запушь код
Замени `YOUR_USERNAME` на свой GitHub username и выполни:

```bash
cd ~/Projects/shoesbot

# Добавь remote
git remote add origin https://github.com/YOUR_USERNAME/shoesbot.git

# Запушь основной код
git push -u origin main

# Запушь тег v1.0.0
git push origin v1.0.0
```

## Готово!
Репозиторий будет доступен по адресу:
https://github.com/YOUR_USERNAME/shoesbot

## Что будет в репозитории:
- ✅ Весь код бота (модульная архитектура)
- ✅ README.md с документацией
- ✅ requirements.txt
- ✅ START.sh для запуска
- ✅ Тег v1.0.0
- ❌ .env (токен бота) - НЕ будет, т.к. в .gitignore
- ❌ data/ и логи - НЕ будут (в .gitignore)

