#!/usr/bin/env python3
"""
Тестовый скрипт для проверки сбора данных из TrainingPeaks и MyNetDiary
Показывает что именно происходит при сборе данных
"""
import os
import sys
from datetime import date, datetime

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(__file__))

from shoesbot.fitness_reporter import FitnessReporter
from shoesbot.trainingpeaks_client import TrainingPeaksClient
from shoesbot.mynetdiary_client import MyNetDiaryClient
from shoesbot.logging_setup import logger

def test_trainingpeaks():
    """Тест сбора данных из TrainingPeaks"""
    print("\n" + "="*60)
    print("ТЕСТ: TrainingPeaks")
    print("="*60)
    
    client = TrainingPeaksClient()
    
    if not client.access_token:
        print("❌ TrainingPeaks не настроен")
        print("   Нужно установить в .env:")
        print("   - TRAININGPEAKS_CLIENT_ID")
        print("   - TRAININGPEAKS_CLIENT_SECRET")
        print("   - TRAININGPEAKS_ACCESS_TOKEN")
        print("   - TRAININGPEAKS_REFRESH_TOKEN")
        print("\n   Или выполнить OAuth авторизацию (см. FITNESS_SETUP.md)")
        return None
    
    print(f"✓ Access token установлен: {client.access_token[:20]}...")
    
    try:
        today = date.today()
        print(f"\n📅 Запрашиваю тренировки за {today}...")
        
        workouts = client.get_workouts(
            start_date=datetime.combine(today, datetime.min.time()),
            end_date=datetime.combine(today, datetime.max.time())
        )
        
        print(f"✓ Получено тренировок: {len(workouts)}")
        
        if workouts:
            print("\nДетали:")
            for i, workout in enumerate(workouts, 1):
                workout_date = workout.get("workoutDate", "N/A")
                workout_type = workout.get("workoutType", {}).get("name", "N/A")
                duration = workout.get("duration", 0)
                distance = workout.get("distance", 0)
                
                print(f"  {i}. {workout_date} - {workout_type}")
                if duration:
                    hours = duration // 3600
                    minutes = (duration % 3600) // 60
                    print(f"     Длительность: {hours}ч {minutes}м")
                if distance:
                    print(f"     Дистанция: {distance/1000:.2f} км")
        else:
            print("  (Тренировок за сегодня нет)")
        
        return workouts
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_mynetdiary():
    """Тест сбора данных из MyNetDiary"""
    print("\n" + "="*60)
    print("ТЕСТ: MyNetDiary")
    print("="*60)
    
    client = MyNetDiaryClient()
    
    # Проверяем CSV путь
    csv_path = client.csv_export_path
    if csv_path:
        print(f"✓ CSV путь установлен: {csv_path}")
        if os.path.exists(csv_path):
            print(f"✓ Файл существует")
        else:
            print(f"❌ Файл не найден!")
            return None
    else:
        print("❌ CSV путь не установлен")
        print("   Установите в .env: MYNETDIARY_CSV_PATH=/path/to/export.csv")
        
        # Проверяем веб-скрапинг
        if client.username and client.password:
            print(f"\n✓ Попытка веб-скрапинга (username: {client.username})...")
            print("  ⚠️  Внимание: веб-скрапинг пока не реализован полностью")
        else:
            print("   Или установите: MYNETDIARY_USERNAME и MYNETDIARY_PASSWORD")
        
        return None
    
    try:
        print(f"\n📅 Читаю данные за {date.today()}...")
        
        nutrition = client.get_today_nutrition()
        
        if nutrition:
            print("✓ Данные получены:")
            print(f"  Дата: {nutrition.get('date')}")
            calories = nutrition.get('calories')
            if calories:
                print(f"  Калории: {calories:.0f} ккал")
            
            meals = nutrition.get('meals', [])
            if meals:
                print(f"  Приемов пищи: {len(meals)}")
                meals_by_type = {}
                for meal in meals:
                    meal_type = meal.get('meal', 'Другое')
                    if meal_type not in meals_by_type:
                        meals_by_type[meal_type] = []
                    meals_by_type[meal_type].append(meal)
                
                for meal_type, meal_list in meals_by_type.items():
                    print(f"\n  {meal_type}:")
                    for meal in meal_list:
                        food = meal.get('food', '')
                        cal = meal.get('calories', 0)
                        if food:
                            print(f"    • {food} ({cal:.0f} ккал)")
            else:
                print("  (Приемов пищи не найдено)")
            
            return nutrition
        else:
            print("  (Данных за сегодня нет в CSV)")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_chatgpt_report():
    """Тест генерации отчета через ChatGPT"""
    print("\n" + "="*60)
    print("ТЕСТ: Генерация отчета через ChatGPT")
    print("="*60)
    
    reporter = FitnessReporter()
    
    if not reporter.chatgpt.api_key:
        print("❌ OpenAI API ключ не установлен")
        print("   Установите в .env: OPENAI_API_KEY=sk-...")
        return None
    
    print(f"✓ OpenAI API ключ установлен: {reporter.chatgpt.api_key[:20]}...")
    
    try:
        print("\n📊 Генерирую отчет...")
        
        report_text, success = reporter.get_daily_report()
        
        if success:
            print("✓ Отчет сгенерирован:")
            print("\n" + "-"*60)
            print(report_text)
            print("-"*60)
        else:
            print(f"⚠️  {report_text}")
        
        return report_text
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Запуск всех тестов"""
    print("="*60)
    print("ТЕСТИРОВАНИЕ СБОРА ДАННЫХ")
    print("TrainingPeaks + MyNetDiary → ChatGPT → Отчет")
    print("="*60)
    
    # Тест 1: TrainingPeaks
    workouts = test_trainingpeaks()
    
    # Тест 2: MyNetDiary
    nutrition = test_mynetdiary()
    
    # Тест 3: ChatGPT отчет
    report = test_chatgpt_report()
    
    # Итоги
    print("\n" + "="*60)
    print("ИТОГИ")
    print("="*60)
    
    if workouts is not None:
        print(f"✓ TrainingPeaks: {len(workouts) if workouts else 0} тренировок")
    else:
        print("✗ TrainingPeaks: не настроен")
    
    if nutrition is not None:
        calories = nutrition.get('calories', 0)
        meals_count = len(nutrition.get('meals', []))
        print(f"✓ MyNetDiary: {calories:.0f} ккал, {meals_count} приемов пищи")
    else:
        print("✗ MyNetDiary: не настроен")
    
    if report:
        print(f"✓ ChatGPT: отчет сгенерирован ({len(report)} символов)")
    else:
        print("✗ ChatGPT: ошибка генерации")
    
    print("\n" + "="*60)
    print("Для настройки см. FITNESS_SETUP.md")
    print("Для понимания процесса см. FITNESS_HOW_IT_WORKS.md")
    print("="*60)

if __name__ == "__main__":
    main()

