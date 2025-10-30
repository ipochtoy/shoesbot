from shoesbot.telegram_bot import build_app

if __name__ == "__main__":
    app = build_app()
    app.run_polling()
