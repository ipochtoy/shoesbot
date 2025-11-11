"""
ChatGPT Reporter
Генерация отчетов о тренировках и питании через ChatGPT API
"""
import os
import json
from typing import Optional, Dict, List
from shoesbot.logging_setup import logger


class ChatGPTReporter:
    """Генератор отчетов через ChatGPT"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Инициализация репортера
        
        Args:
            api_key: OpenAI API ключ
            model: Модель для использования (gpt-4o-mini, gpt-4o, etc.)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.base_url = "https://api.openai.com/v1/chat/completions"
        
        if not self.api_key:
            logger.warning("OpenAI API key not set. Set OPENAI_API_KEY")
    
    def generate_report(self, workouts_data: Optional[List[Dict]] = None, 
                       nutrition_data: Optional[Dict] = None,
                       language: str = "ru") -> str:
        """
        Сгенерировать отчет о тренировках и питании
        
        Args:
            workouts_data: Данные о тренировках из TrainingPeaks
            nutrition_data: Данные о питании из MyNetDiary
            language: Язык отчета (ru/en)
            
        Returns:
            Сгенерированный отчет
        """
        if not self.api_key:
            return "❌ OpenAI API ключ не настроен"
        
        # Формируем промпт
        system_prompt = """Ты помощник для анализа тренировок и питания. 
Создавай краткие, мотивирующие отчеты на русском языке.
Включай анализ прогресса, рекомендации и позитивный настрой."""
        
        user_prompt_parts = []
        
        if workouts_data:
            workouts_text = self._format_workouts_for_prompt(workouts_data)
            user_prompt_parts.append(f"Тренировки:\n{workouts_text}")
        
        if nutrition_data:
            nutrition_text = self._format_nutrition_for_prompt(nutrition_data)
            user_prompt_parts.append(f"Питание:\n{nutrition_text}")
        
        if not user_prompt_parts:
            return "📊 Данных за сегодня нет"
        
        user_prompt = "\n\n".join(user_prompt_parts)
        user_prompt += "\n\nСоздай краткий мотивирующий отчет на русском языке. Включи анализ и рекомендации."
        
        try:
            import requests
            
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 500
                },
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            report = result["choices"][0]["message"]["content"]
            return report.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate ChatGPT report: {e}")
            return f"❌ Ошибка генерации отчета: {str(e)[:200]}"
    
    def _format_workouts_for_prompt(self, workouts: List[Dict]) -> str:
        """Форматировать тренировки для промпта"""
        if not workouts:
            return "Тренировок не было"
        
        lines = []
        for workout in workouts:
            workout_date = workout.get("workoutDate", "")
            workout_type = workout.get("workoutType", {}).get("name", "Неизвестно")
            duration = workout.get("duration", 0)
            distance = workout.get("distance", 0)
            
            line = f"- {workout_date}: {workout_type}"
            if duration:
                hours = duration // 3600
                minutes = (duration % 3600) // 60
                line += f", {hours}ч {minutes}м"
            if distance:
                line += f", {distance/1000:.2f} км"
            lines.append(line)
        
        return "\n".join(lines)
    
    def _format_nutrition_for_prompt(self, nutrition: Dict) -> str:
        """Форматировать питание для промпта"""
        lines = []
        
        calories = nutrition.get('calories')
        if calories:
            lines.append(f"Калории: {calories:.0f} ккал")
        
        meals = nutrition.get('meals', [])
        if meals:
            meals_by_type = {}
            for meal in meals:
                meal_type = meal.get('meal', 'Другое')
                if meal_type not in meals_by_type:
                    meals_by_type[meal_type] = []
                meals_by_type[meal_type].append(meal)
            
            for meal_type, meal_list in meals_by_type.items():
                meal_foods = [m.get('food', '') for m in meal_list if m.get('food')]
                if meal_foods:
                    lines.append(f"{meal_type}: {', '.join(meal_foods)}")
        
        return "\n".join(lines) if lines else "Данных о питании нет"

