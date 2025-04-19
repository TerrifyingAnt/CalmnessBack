import logging
import numpy as np
from transformers import pipeline, AutoModelForSequenceClassification, AutoTokenizer

logger = logging.getLogger(__name__)

class EmotionService:
    def __init__(self):
        try:
            # Инициализация моделей при создании экземпляра сервиса
            # Модель для определения общего эмоционального тона (от -1 до 1)
            self.sentiment_analyzer = pipeline(
                "sentiment-analysis", 
                model="blanchefort/rubert-base-cased-sentiment"
            )
            
            # Модель для классификации конкретных эмоций
            emotion_model_name = "cointegrated/rubert-tiny-emotion"
            self.emotion_model = AutoModelForSequenceClassification.from_pretrained(emotion_model_name)
            self.emotion_tokenizer = AutoTokenizer.from_pretrained(emotion_model_name)
            self.emotions = ["нейтральность", "радость", "грусть", "удивление", "страх", "гнев"]
            
            logger.info("Эмоциональные модели успешно загружены")
        except Exception as e:
            logger.error(f"Ошибка при инициализации моделей эмоций: {str(e)}")
            # Установим None для моделей, чтобы сервис мог работать в режиме отказоустойчивости
            self.sentiment_analyzer = None
            self.emotion_model = None
            self.emotion_tokenizer = None
            self.emotions = []
    
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

# Экземпляр для использования в других модулях
emotion_service = EmotionService() 