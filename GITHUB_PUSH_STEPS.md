# Инструкции по пушу в GitHub

## Способ 1: GitHub CLI (рекомендуется)

### Шаг 1: Авторизация

Откройте терминал и выполните:

```bash
cd ~/Projects/shoesbot
gh auth login --web
```

- Откроется браузер
- Войдите в GitHub
- Нажмите "Authorize"

### Шаг 2: Проверка

```bash
gh auth status
```

Должно показать: `Logged in to github.com as [ваш-username]`

### Шаг 3: Пуш

```bash
git push origin main
```

## Способ 2: Через Cursor UI

1. В Cursor откройте Source Control (Cmd+Shift+G)
2. Убедитесь что все изменения закоммичены (зелёная галочка)
3. Нажмите на три точки (...) в панели Git
4. Выберите "Push" или "Push to..."
5. Выберите remote "origin" и ветку "main"

## Альтернатива: HTTPS с токеном

Если CLI не работает, используйте личный токен:

1. Создайте токен: https://github.com/settings/tokens/new
2. Дайте права: `repo`
3. Скопируйте токен
4. Выполните:

```bash
cd ~/Projects/shoesbot
git push https://YOUR_TOKEN@github.com/ipochtoy/shoesbot.git main
```

Замените `YOUR_TOKEN` на ваш токен.

## Проверка результата

Откройте в браузере: https://github.com/ipochtoy/shoesbot

