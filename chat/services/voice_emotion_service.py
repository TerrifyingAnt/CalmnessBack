import logging
import numpy as np
import tempfile
import os
from typing import Tuple, Optional
import librosa
import torch
from transformers import AutoModelForAudioClassification, AutoFeatureExtractor

logger = logging.getLogger(__name__)

class VoiceEmotionService:
    def __init__(self):
        try:
            # Initialize the model and feature extractor for emotion recognition from audio
            # Using a pre-trained model for speech emotion recognition
            model_name = "ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition"
            self.model = AutoModelForAudioClassification.from_pretrained(model_name)
            self.feature_extractor = AutoFeatureExtractor.from_pretrained(model_name)
            
            # Emotion labels for the model
            self.emotions = ["angry", "calm", "disgust", "fear", "happiness", "neutral", "sadness", "surprise"]
            
            # Mapping to standardized emotion values we use in the app
            self.emotion_map = {
                "angry": "anger",
                "calm": "calm",
                "disgust": "disgust",
                "fear": "fear",
                "happiness": "happiness",
                "neutral": "calm",
                "sadness": "sadness",
                "surprise": "surprise"
            }
            
            logger.info("Voice emotion models successfully loaded")
        except Exception as e:
            logger.error(f"Error initializing voice emotion models: {str(e)}")
            self.model = None
            self.feature_extractor = None
            self.emotions = []
            self.emotion_map = {}
    
    async def analyze_audio_file(self, audio_data: bytes, file_name: str) -> Tuple[float, str]:
        """
        Analyze audio data for emotional content
        
        Args:
            audio_data: Raw bytes of the audio file
            file_name: Name of the audio file (used to determine format)
            
        Returns:
            Tuple[float, str]: Emotional state (-1 to 1) and emotion label
        """
        if not self.model or not self.feature_extractor:
            logger.warning("Voice emotion model not initialized, returning default values")
            return 0.0, "calm"
        
        try:
            # Save audio data to a temporary file
            with tempfile.NamedTemporaryFile(suffix=os.path.splitext(file_name)[1], delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name
            
            # Load and preprocess audio
            try:
                # Load audio with librosa (handles various formats)
                audio_array, sampling_rate = librosa.load(temp_path, sr=16000)
                
                # Remove temporary file
                os.unlink(temp_path)
                
                # Extract features
                inputs = self.feature_extractor(
                    audio_array, 
                    sampling_rate=sampling_rate, 
                    return_tensors="pt"
                )
                
                # Get model predictions
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    logits = outputs.logits
                    
                # Get predicted class and confidence
                predicted_class_id = torch.argmax(logits, dim=1).item()
                probabilities = torch.nn.functional.softmax(logits, dim=1)[0]
                confidence = probabilities[predicted_class_id].item()
                
                # Get emotion name
                emotion = self.emotions[predicted_class_id]
                standardized_emotion = self.emotion_map.get(emotion, "calm")
                
                # Calculate emotional state value (-1 to 1)
                # Map negative emotions to negative values, positive to positive
                emotional_state = 0.0
                if emotion in ["happiness", "calm", "surprise"]:
                    emotional_state = confidence  # 0 to 1
                elif emotion in ["angry", "disgust", "fear", "sadness"]:
                    emotional_state = -confidence  # -1 to 0
                
                logger.info(f"Voice emotion analysis: {emotion} with confidence {confidence}")
                return emotional_state, standardized_emotion
                
            except Exception as e:
                logger.error(f"Error processing audio file: {str(e)}")
                os.unlink(temp_path)  # Ensure temp file is removed
                return 0.0, "calm"
                
        except Exception as e:
            logger.error(f"Error analyzing voice emotion: {str(e)}")
            return 0.0, "calm"
    
    def get_valence_from_emotion(self, emotion: str) -> float:
        """
        Convert emotion label to valence score (-1 to 1)
        Useful as a fallback when direct analysis fails
        """
        emotion_valence = {
            "anger": -0.8,
            "disgust": -0.6,
            "fear": -0.7,
            "sadness": -0.5,
            "surprise": 0.4,
            "happiness": 0.8,
            "calm": 0.3
        }
        return emotion_valence.get(emotion, 0.0)

# Create a singleton instance
voice_emotion_service = VoiceEmotionService()