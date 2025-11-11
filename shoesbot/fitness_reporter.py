"""
Fitness Reporter
Объединяет данные из TrainingPeaks и MyNetDiary, генерирует отчет через ChatGPT
"""
from datetime import datetime, date
from typing import Optional, Tuple
from shoesbot.logging_setup import logger
from shoesbot.trainingpeaks_client import TrainingPeaksClient
from shoesbot.mynetdiary_client import MyNetDiaryClient
from shoesbot.chatgpt_reporter import ChatGPTReporter


class FitnessReporter:
    """Главный класс для генерации отчетов о тренировках и питании"""
    
    def __init__(self):
        """Инициализация всех клиентов"""
        self.tp_client = TrainingPeaksClient()
        self.mnd_client = MyNetDiaryClient()
        self.chatgpt = ChatGPTReporter()
    
    def get_daily_report(self, target_date: Optional[date] = None) -> Tuple[str, bool]:
        """
        Получить ежедневный отчет
        
        Args:
            target_date: Дата для отчета (по умолчанию сегодня)
            
        Returns:
            Кортеж (отчет, успешно ли сгенерирован)
        """
        if not target_date:
            target_date = date.today()
        
        workouts_data = None
        nutrition_data = None
        
        # Получаем данные о тренировках
        try:
            if self.tp_client.access_token:
                workouts = self.tp_client.get_workouts(
                    start_date=datetime.combine(target_date, datetime.min.time()),
                    end_date=datetime.combine(target_date, datetime.max.time())
                )
                workouts_data = workouts if workouts else None
                logger.info(f"Got {len(workouts) if workouts else 0} workouts from TrainingPeaks")
            else:
                logger.warning("TrainingPeaks not configured")
        except Exception as e:
            logger.error(f"Failed to get TrainingPeaks data: {e}")
        
        # Получаем данные о питании
        try:
            nutrition_data = self.mnd_client.get_today_nutrition()
            if nutrition_data:
                logger.info(f"Got nutrition data from MyNetDiary")
            else:
                logger.warning("No nutrition data from MyNetDiary")
        except Exception as e:
            logger.error(f"Failed to get MyNetDiary data: {e}")
        
        # Если нет данных вообще
        if not workouts_data and not nutrition_data:
            return "📊 Данных за сегодня нет. Проверьте настройки TrainingPeaks и MyNetDiary.", False
        
        # Генерируем отчет через ChatGPT
        try:
            report = self.chatgpt.generate_report(
                workouts_data=workouts_data,
                nutrition_data=nutrition_data
            )
            return report, True
        except Exception as e:
            logger.error(f"Failed to generate ChatGPT report: {e}")
            # Fallback на простой формат
            return self._generate_simple_report(workouts_data, nutrition_data), True
    
    def _generate_simple_report(self, workouts_data: Optional[list], nutrition_data: Optional[dict]) -> str:
        """Простой отчет без ChatGPT"""
        lines = ["📊 Отчет за сегодня\n"]
        
        if workouts_data:
            lines.append(self.tp_client.format_workouts_summary(workouts_data))
            lines.append("")
        
        if nutrition_data:
            lines.append(self.mnd_client.format_nutrition_summary(nutrition_data))
        
        return "\n".join(lines)

