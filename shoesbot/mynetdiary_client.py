"""
MyNetDiary Client
Поддержка экспорта данных через CSV или веб-скрапинг
"""
import os
import csv
import requests
from datetime import datetime, date
from typing import Optional, Dict, List
from pathlib import Path
from shoesbot.logging_setup import logger


class MyNetDiaryClient:
    """Клиент для работы с данными MyNetDiary"""
    
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None,
                 csv_export_path: Optional[str] = None):
        """
        Инициализация клиента
        
        Args:
            username: Логин MyNetDiary
            password: Пароль MyNetDiary
            csv_export_path: Путь к CSV файлу экспорта (если используется ручной экспорт)
        """
        self.username = username or os.getenv("MYNETDIARY_USERNAME")
        self.password = password or os.getenv("MYNETDIARY_PASSWORD")
        self.csv_export_path = csv_export_path or os.getenv("MYNETDIARY_CSV_PATH")
        self.session = None
    
    def login(self) -> bool:
        """
        Авторизация в MyNetDiary (если нужен веб-скрапинг)
        
        Returns:
            True если успешно
        """
        if not self.username or not self.password:
            logger.warning("MyNetDiary credentials not set")
            return False
        
        try:
            self.session = requests.Session()
            # MyNetDiary использует форму логина
            login_url = "https://www.mynetdiary.com/login.do"
            
            # Получаем страницу логина для получения CSRF токена
            response = self.session.get(login_url)
            response.raise_for_status()
            
            # Отправляем данные логина
            login_data = {
                "username": self.username,
                "password": self.password,
                "action": "login"
            }
            
            response = self.session.post(login_url, data=login_data)
            response.raise_for_status()
            
            # Проверяем успешность логина
            if "dashboard" in response.url.lower() or "mynetdiary.com/dashboard" in response.text:
                logger.info("MyNetDiary login successful")
                return True
            else:
                logger.warning("MyNetDiary login failed")
                return False
        except Exception as e:
            logger.error(f"MyNetDiary login error: {e}")
            return False
    
    def export_daily_data(self, target_date: Optional[date] = None) -> Optional[Dict]:
        """
        Экспортировать данные за день через веб-интерфейс
        
        Args:
            target_date: Дата (по умолчанию сегодня)
            
        Returns:
            Словарь с данными о питании или None
        """
        if not self.session:
            if not self.login():
                return None
        
        if not target_date:
            target_date = date.today()
        
        try:
            # URL для получения данных за день
            # Формат может отличаться, нужно проверить реальный API MyNetDiary
            dashboard_url = f"https://www.mynetdiary.com/dashboard.do?date={target_date.strftime('%Y-%m-%d')}"
            
            response = self.session.get(dashboard_url)
            response.raise_for_status()
            
            # Парсим HTML (упрощенная версия, может потребоваться BeautifulSoup)
            # Здесь нужен реальный парсинг страницы MyNetDiary
            # Пока возвращаем заглушку
            
            return {
                "date": target_date.isoformat(),
                "calories": None,  # Нужно парсить из HTML
                "meals": []  # Нужно парсить из HTML
            }
        except Exception as e:
            logger.error(f"Failed to export daily data: {e}")
            return None
    
    def read_csv_export(self, csv_path: Optional[str] = None, target_date: Optional[date] = None) -> Optional[Dict]:
        """
        Читать данные из CSV экспорта
        
        Args:
            csv_path: Путь к CSV файлу
            target_date: Дата для фильтрации (по умолчанию сегодня)
            
        Returns:
            Словарь с данными о питании или None
        """
        if not csv_path:
            csv_path = self.csv_export_path
        
        if not csv_path or not Path(csv_path).exists():
            logger.warning(f"CSV file not found: {csv_path}")
            return None
        
        if not target_date:
            target_date = date.today()
        
        try:
            meals = []
            total_calories = 0
            
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Формат CSV может отличаться, нужно адаптировать под реальный формат MyNetDiary
                    row_date_str = row.get('Date', '')
                    try:
                        row_date = datetime.strptime(row_date_str, '%Y-%m-%d').date()
                        if row_date == target_date:
                            meal_name = row.get('Meal', '')
                            food = row.get('Food', '')
                            calories = float(row.get('Calories', 0) or 0)
                            
                            meals.append({
                                "meal": meal_name,
                                "food": food,
                                "calories": calories
                            })
                            total_calories += calories
                    except (ValueError, KeyError):
                        continue
            
            return {
                "date": target_date.isoformat(),
                "calories": total_calories,
                "meals": meals
            }
        except Exception as e:
            logger.error(f"Failed to read CSV: {e}")
            return None
    
    def get_today_nutrition(self) -> Optional[Dict]:
        """
        Получить данные о питании за сегодня
        
        Returns:
            Словарь с данными или None
        """
        # Сначала пробуем CSV, потом веб-скрапинг
        data = self.read_csv_export()
        if data:
            return data
        
        return self.export_daily_data()
    
    def format_nutrition_summary(self, nutrition_data: Optional[Dict]) -> str:
        """
        Форматировать данные о питании в читаемый текст
        
        Args:
            nutrition_data: Данные о питании
            
        Returns:
            Отформатированная строка
        """
        if not nutrition_data:
            return "Данные о питании не найдены"
        
        lines = [f"🍽️ Питание за {nutrition_data.get('date', 'сегодня')}"]
        
        calories = nutrition_data.get('calories')
        if calories:
            lines.append(f"Калории: {calories:.0f} ккал")
        
        meals = nutrition_data.get('meals', [])
        if meals:
            # Группируем по приемам пищи
            meals_by_type = {}
            for meal in meals:
                meal_type = meal.get('meal', 'Другое')
                if meal_type not in meals_by_type:
                    meals_by_type[meal_type] = []
                meals_by_type[meal_type].append(meal)
            
            for meal_type, meal_list in meals_by_type.items():
                lines.append(f"\n{meal_type}:")
                for meal in meal_list:
                    food = meal.get('food', '')
                    meal_cal = meal.get('calories', 0)
                    if food:
                        lines.append(f"  • {food} ({meal_cal:.0f} ккал)")
        else:
            lines.append("Приемы пищи не найдены")
        
        return "\n".join(lines)

