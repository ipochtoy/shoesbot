"""
Daily Fitness Scheduler
Планировщик для ежедневной автоматической отправки отчетов в Telegram
"""
import os
import asyncio
from datetime import datetime, time
from typing import Optional
from shoesbot.logging_setup import logger
from shoesbot.fitness_reporter import FitnessReporter


class DailyFitnessScheduler:
    """Планировщик ежедневных отчетов"""
    
    def __init__(self, bot, target_chat_id: Optional[int] = None, send_time: Optional[time] = None):
        """
        Инициализация планировщика
        
        Args:
            bot: Экземпляр Telegram бота
            target_chat_id: ID чата для отправки (если None, берется из env)
            send_time: Время отправки (по умолчанию 21:00)
        """
        self.bot = bot
        self.target_chat_id = target_chat_id or int(os.getenv("FITNESS_REPORT_CHAT_ID", "0"))
        self.send_time = send_time or time(21, 0)  # 21:00 по умолчанию
        self.reporter = FitnessReporter()
        self.running = False
    
    async def send_daily_report(self) -> bool:
        """
        Отправить ежедневный отчет
        
        Returns:
            True если успешно
        """
        if not self.target_chat_id:
            logger.warning("FITNESS_REPORT_CHAT_ID not set, skipping daily report")
            return False
        
        try:
            report_text, success = self.reporter.get_daily_report()
            
            if not success:
                logger.warning(f"Report generation failed: {report_text}")
                return False
            
            # Создаем кнопку для обновления
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Обновить отчет", callback_data="report:refresh")
            ]])
            
            await self.bot.send_message(
                chat_id=self.target_chat_id,
                text=report_text,
                reply_markup=kb,
                parse_mode='HTML'
            )
            
            logger.info(f"Daily fitness report sent to chat {self.target_chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send daily report: {e}", exc_info=True)
            return False
    
    async def _scheduler_loop(self):
        """Основной цикл планировщика"""
        self.running = True
        logger.info(f"Daily fitness scheduler started. Send time: {self.send_time}")
        
        while self.running:
            try:
                now = datetime.now()
                target_datetime = datetime.combine(now.date(), self.send_time)
                
                # Если время уже прошло сегодня, планируем на завтра
                if target_datetime < now:
                    from datetime import timedelta
                    target_datetime = datetime.combine(
                        (now + timedelta(days=1)).date(),
                        self.send_time
                    )
                
                # Вычисляем время до следующей отправки
                wait_seconds = (target_datetime - now).total_seconds()
                logger.info(f"Next report scheduled for {target_datetime}, waiting {wait_seconds:.0f} seconds")
                
                # Ждем до времени отправки
                await asyncio.sleep(wait_seconds)
                
                # Отправляем отчет
                await self.send_daily_report()
                
            except asyncio.CancelledError:
                logger.info("Scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}", exc_info=True)
                # Ждем минуту перед повтором при ошибке
                await asyncio.sleep(60)
    
    def start(self):
        """Запустить планировщик в фоне"""
        if self.running:
            logger.warning("Scheduler already running")
            return
        
        # Создаем задачу в event loop
        loop = asyncio.get_event_loop()
        loop.create_task(self._scheduler_loop())
        logger.info("Daily fitness scheduler task created")
    
    def stop(self):
        """Остановить планировщик"""
        self.running = False
        logger.info("Daily fitness scheduler stopped")

