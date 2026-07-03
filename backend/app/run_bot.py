import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

from app.services.telegram_bot_service import telegram_bot


async def main():
    telegram_bot.configure()
    app = telegram_bot.build_application()
    if not app:
        print("Telegram bot not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_ADMIN_CHAT_ID in .env")
        return
    print("Starting Telegram bot polling...")
    async with app:
        await app.start()
        await telegram_bot._set_menu_commands(app)
        print("Bot is running. Press Ctrl+C to stop.")
        await app.updater.start_polling(drop_pending_updates=True)
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            pass
        finally:
            await app.updater.stop()
            await app.stop()


if __name__ == "__main__":
    asyncio.run(main())
