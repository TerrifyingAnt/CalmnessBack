import logging
import numpy as np
import os
import urllib.request
import tempfile
from typing import Optional
import librosa
from transformers import pipeline, AutoModelForSequenceClassification, AutoTokenizer

logger = logging.getLogger(__name__)

class EmotionService:
    def __init__(self):
        try:
            # Инициализация моделей для текста
            # Модель для определения общего эмоционального тона (от -1 до 1)
            self.sentiment_analyzer = pipeline(
                "sentiment-analysis", 
                model="blanchefort/rubert-base-cased-sentiment"
            )
            
            # Модель для классификации конкретных эмоций в тексте
            emotion_model_name = "cointegrated/rubert-tiny2-cedr-emotion-detection"
            self.emotion_model = AutoModelForSequenceClassification.from_pretrained(emotion_model_name)
            self.emotion_tokenizer = AutoTokenizer.from_pretrained(emotion_model_name)
            self.emotions = ["нейтральность", "радость", "грусть", "удивление", "страх", "гнев"]
            
            # Инициализация моделей для аудио
            # Модель для определения эмоций в голосе (русский язык)
            # Используем ту же модельную архитектуру для голосовых сообщений
            self.voice_sentiment_model = pipeline(
                "audio-classification", 
                model="xbgoose/hubert-speech-emotion-recognition-russian"
            )
            
            logger.info("Эмоциональные модели успешно загружены")
        except Exception as e:
            logger.error(f"Ошибка при инициализации моделей эмоций: {str(e)}")
            # Установим None для моделей, чтобы сервис мог работать в режиме отказоустойчивости
            self.sentiment_analyzer = None
            self.emotion_model = None
            self.emotion_tokenizer = None
            self.emotions = []
            self.voice_sentiment_model = None
    
    def analyze_sentiment(self, text: str) -> float:
        """
        Анализ эмоционального тона текста, возвращает значение от -1 до 1
        """
        if not text or not self.sentiment_analyzer:
            return 0.0  # Нейтральное значение по умолчанию
            
        try:
            # Анализируем сентимент текста
            result = self.sentiment_analyzer(text)
            
            # Русские модели часто возвращают POSITIVE/NEGATIVE/NEUTRAL, преобразуем в числовое значение
            if result[0]["label"] == "POSITIVE":
                score = result[0]["score"]  # 0-1
                return score  # Уже в диапазоне от 0 до 1, просто используем
            elif result[0]["label"] == "NEGATIVE":
                score = result[0]["score"]  # 0-1
                return -score  # Отрицательное значение для негативного сентимента
            else:
                return 0.0  # Нейтральное значение
        except Exception as e:
            logger.error(f"Ошибка при анализе сентимента: {str(e)}")
            return 0.0
    
    def classify_emotion(self, text: str) -> str:
        """
        Классификация конкретной эмоции в тексте
        """
        if not text or not self.emotion_model or not self.emotion_tokenizer:
            return "нейтральность"  # Значение по умолчанию
            
        try:
            # Токенизация и получение предсказаний
            inputs = self.emotion_tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            outputs = self.emotion_model(**inputs)
            probs = outputs.logits.softmax(dim=1).detach().numpy()[0]
            
            # Определяем эмоцию с наивысшим значением вероятности
            emotion_idx = np.argmax(probs)
            emotion = self.emotions[emotion_idx]
            
            # Маппинг на английские названия для единообразия с требованием задачи
            emotion_map = {
                "нейтральность": "calm",
                "радость": "happiness",
                "грусть": "sadness",
                "удивление": "surprise",
                "страх": "fear",
                "гнев": "anger"
            }
            
            return emotion_map.get(emotion, "calm")
        except Exception as e:
            logger.error(f"Ошибка при классификации эмоции: {str(e)}")
            return "calm"  # Значение по умолчанию

    def analyze_voice_sentiment(self, voice_url: str) -> float:
        """
        Анализ эмоционального тона голосового сообщения, возвращает значение от -1 до 1
        """
        if not voice_url or not self.voice_sentiment_model:
            return 0.0  # Нейтральное значение по умолчанию
            
        try:
            # Скачиваем аудиофайл во временную директорию
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(voice_url.split('?')[0])[1]) as temp_file:
                urllib.request.urlretrieve(voice_url, temp_file.name)
                temp_path = temp_file.name
                
            # Загружаем аудиофайл с помощью librosa и извлекаем аудиофичи
            audio, sr = librosa.load(temp_path, sr=16000, mono=True)
            
            # Выполняем классификацию эмоций с помощью модели
            result = self.voice_sentiment_model(temp_path)
            
            # Преобразуем результат классификации в значение от -1 до 1
            sentiment_map = {
                "neutral": 0.0,
                "positive": 0.7,
                "negative": -0.7,
                "angry": -0.9,
                "sad": -0.6,
                "happy": 0.9,
                "fear": -0.8,
                "surprise": 0.5
            }
            
            # Найдем эмоцию с наивысшим значением
            top_emotion = max(result, key=lambda x: x['score'])
            
            # Получаем соответствующее значение из карты
            sentiment_score = sentiment_map.get(top_emotion['label'].lower(), 0.0)
            
            # Удаляем временный файл
            os.unlink(temp_path)
            
            return sentiment_score
            
        except Exception as e:
            logger.error(f"Ошибка при анализе сентимента голосового сообщения: {str(e)}")
            return 0.0
    
    def classify_voice_emotion(self, voice_url: str) -> str:
        """
        Классификация конкретной эмоции в голосовом сообщении
        """
        if not voice_url or not self.voice_sentiment_model:
            return "calm"  # Значение по умолчанию
            
        try:
            # Скачиваем аудиофайл во временную директорию
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(voice_url.split('?')[0])[1]) as temp_file:
                urllib.request.urlretrieve(voice_url, temp_file.name)
                temp_path = temp_file.name
                
            # Выполняем классификацию эмоций с помощью модели
            result = self.voice_sentiment_model(temp_path)
            
            # Маппинг на английские названия для единообразия с требованием задачи
            emotion_map = {
                "neutral": "calm",
                "positive": "happiness",
                "negative": "sadness",
                "angry": "anger",
                "sad": "sadness",
                "happy": "happiness",
                "fear": "fear",
                "surprise": "surprise"
            }
            
            # Найдем эмоцию с наивысшим значением
            top_emotion = max(result, key=lambda x: x['score'])
            
            # Получаем соответствующее значение из карты
            mapped_emotion = emotion_map.get(top_emotion['label'].lower(), "calm")
            
            # Удаляем временный файл
            os.unlink(temp_path)
            
            return mapped_emotion
            
        except Exception as e:
            logger.error(f"Ошибка при классификации эмоции голосового сообщения: {str(e)}")
            return "calm"  # Значение по умолчанию

# Экземпляр для использования в других модулях
emotion_service = EmotionService()