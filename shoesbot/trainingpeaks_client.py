"""
TrainingPeaks API Client
Использует OAuth 2.0 для получения данных о тренировках
"""
import os
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from shoesbot.logging_setup import logger


class TrainingPeaksClient:
    """Клиент для работы с TrainingPeaks API"""
    
    BASE_URL = "https://api.trainingpeaks.com"
    
    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None, 
                 access_token: Optional[str] = None, refresh_token: Optional[str] = None):
        """
        Инициализация клиента
        
        Args:
            client_id: Client ID из TrainingPeaks Developer Portal
            client_secret: Client Secret из TrainingPeaks Developer Portal
            access_token: Текущий access token (если есть)
            refresh_token: Refresh token для обновления access token
        """
        self.client_id = client_id or os.getenv("TRAININGPEAKS_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("TRAININGPEAKS_CLIENT_SECRET")
        self.access_token = access_token or os.getenv("TRAININGPEAKS_ACCESS_TOKEN")
        self.refresh_token = refresh_token or os.getenv("TRAININGPEAKS_REFRESH_TOKEN")
        
        if not self.client_id or not self.client_secret:
            logger.warning("TrainingPeaks credentials not set. Set TRAININGPEAKS_CLIENT_ID and TRAININGPEAKS_CLIENT_SECRET")
    
    def get_authorization_url(self, redirect_uri: str) -> str:
        """
        Получить URL для авторизации OAuth 2.0
        
        Args:
            redirect_uri: URI для редиректа после авторизации
            
        Returns:
            URL для авторизации
        """
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": "workouts.read"
        }
        return f"{self.BASE_URL}/oauth2/authorize?" + "&".join([f"{k}={v}" for k, v in params.items()])
    
    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict:
        """
        Обмен authorization code на access и refresh tokens
        
        Args:
            code: Authorization code из редиректа
            redirect_uri: Тот же redirect_uri что использовался для авторизации
            
        Returns:
            Словарь с access_token и refresh_token
        """
        response = requests.post(
            f"{self.BASE_URL}/oauth2/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
        )
        response.raise_for_status()
        tokens = response.json()
        self.access_token = tokens["access_token"]
        self.refresh_token = tokens["refresh_token"]
        return tokens
    
    def refresh_access_token(self) -> str:
        """
        Обновить access token используя refresh token
        
        Returns:
            Новый access token
        """
        if not self.refresh_token:
            raise ValueError("No refresh token available")
        
        response = requests.post(
            f"{self.BASE_URL}/oauth2/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
        )
        response.raise_for_status()
        tokens = response.json()
        self.access_token = tokens["access_token"]
        if "refresh_token" in tokens:
            self.refresh_token = tokens["refresh_token"]
        return self.access_token
    
    def _ensure_token(self):
        """Убедиться что access token валиден"""
        if not self.access_token:
            if self.refresh_token:
                self.refresh_access_token()
            else:
                raise ValueError("No access token or refresh token available")
    
    def get_workouts(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict]:
        """
        Получить список тренировок за период
        
        Args:
            start_date: Начало периода (по умолчанию сегодня)
            end_date: Конец периода (по умолчанию сегодня)
            
        Returns:
            Список тренировок
        """
        self._ensure_token()
        
        if not start_date:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if not end_date:
            end_date = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # TrainingPeaks API использует формат YYYY-MM-DD
        params = {
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate": end_date.strftime("%Y-%m-%d")
        }
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/v1/workouts",
                params=params,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch workouts: {e}")
            # Если токен истек, пробуем обновить
            if response.status_code == 401 and self.refresh_token:
                logger.info("Token expired, refreshing...")
                self.refresh_access_token()
                headers["Authorization"] = f"Bearer {self.access_token}"
                response = requests.get(
                    f"{self.BASE_URL}/v1/workouts",
                    params=params,
                    headers=headers
                )
                response.raise_for_status()
                return response.json()
            raise
    
    def get_today_workouts(self) -> List[Dict]:
        """Получить тренировки за сегодня"""
        today = datetime.now()
        return self.get_workouts(start_date=today, end_date=today)
    
    def format_workouts_summary(self, workouts: List[Dict]) -> str:
        """
        Форматировать тренировки в читаемый текст
        
        Args:
            workouts: Список тренировок из API
            
        Returns:
            Отформатированная строка
        """
        if not workouts:
            return "Тренировок не найдено"
        
        lines = [f"🏃 Тренировок: {len(workouts)}"]
        for workout in workouts:
            workout_date = workout.get("workoutDate", "")
            workout_type = workout.get("workoutType", {}).get("name", "Неизвестно")
            duration = workout.get("duration", 0)
            distance = workout.get("distance", 0)
            
            lines.append(f"\n📅 {workout_date}")
            lines.append(f"   Тип: {workout_type}")
            if duration:
                hours = duration // 3600
                minutes = (duration % 3600) // 60
                lines.append(f"   Длительность: {hours}ч {minutes}м")
            if distance:
                lines.append(f"   Дистанция: {distance/1000:.2f} км")
        
        return "\n".join(lines)

