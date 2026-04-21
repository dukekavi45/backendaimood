import os
import base64
import json
import numpy as np
import tensorflow as tf
from io import BytesIO
from PIL import Image
import requests
import datetime
import cv2

# ── Debug Logging helper ───────────────────────────────────────────────────
def debug_log(msg):
    log_path = os.path.join(os.path.dirname(__file__), 'debug.log')
    time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(f"[{time_str}] {msg}\n")
    print(msg) 

# ── Emotion → music seed mapping ─────────────────────────────────────────────
EMOTION_SEED_MAP = {
    "happy":     {"valence": 0.85, "energy": 0.80, "genres": ["pop", "dance", "feel-good"], "emoji": "😊"},
    "sad":       {"valence": 0.20, "energy": 0.30, "genres": ["sad", "acoustic", "indie"], "emoji": "😢"},
    "angry":     {"valence": 0.30, "energy": 0.90, "genres": ["metal", "rock", "hip-hop"], "emoji": "😡"},
    "fear":      {"valence": 0.25, "energy": 0.60, "genres": ["ambient", "cinematic", "dark-ambient"], "emoji": "😨"},
    "surprise":  {"valence": 0.70, "energy": 0.75, "genres": ["electro", "pop", "indie-pop"], "emoji": "😲"},
    "neutral":   {"valence": 0.50, "energy": 0.50, "genres": ["chill", "lo-fi", "indie"], "emoji": "😐"},
    "disgust":   {"valence": 0.25, "energy": 0.55, "genres": ["punk", "alternative", "grunge"], "emoji": "🤢"},
    "calm":      {"valence": 0.65, "energy": 0.25, "genres": ["ambient", "classical", "meditation"], "emoji": "😌"},
    "excited":   {"valence": 0.90, "energy": 0.95, "genres": ["edm", "pop", "dance"], "emoji": "🤩"},
    "melancholy":{"valence": 0.30, "energy": 0.35, "genres": ["indie", "folk", "singer-songwriter"], "emoji": "😞"},
    "romantic":  {"valence": 0.70, "energy": 0.40, "genres": ["romance", "acoustic", "r-n-b"], "emoji": "💍"},
    "workout":   {"valence": 0.60, "energy": 0.95, "genres": ["rock", "hip-hop", "techno"], "emoji": "💪"},
    "party":     {"valence": 0.85, "energy": 0.90, "genres": ["party", "dance", "pop"], "emoji": "🎉"},
    "focus":     {"valence": 0.50, "energy": 0.30, "genres": ["lo-fi", "ambient", "chill"], "emoji": "📚"},
    "telugu":    {"valence": 0.75, "energy": 0.70, "genres": ["telugu", "indian"], "emoji": "🎵"},
}

TEXT_MOOD_MAP = {
    # Emoji Support
    "💍": "romantic", "💖": "romantic", "❤️": "romantic", "🌹": "romantic", "🥰": "romantic",
    "💌": "romantic", "👰": "romantic", "🤤": "romantic",
    "😒": "angry", "😠": "angry", "😡": "angry", "🤬": "angry",
    "😉": "happy", "😊": "happy", "😄": "happy", "🥳": "happy", "😁": "happy",
    "😎": "excited", "🔥": "excited", "🤩": "excited",
    "🎶": "party", "💃": "party", "🕺": "party", "🎉": "party",
    "😢": "sad", "😭": "sad", "😞": "sad", "💔": "sad", "🥺": "sad",
    "😴": "focus", "📚": "focus", "💻": "focus", "🧘": "focus",
    "😱": "surprise", "😲": "surprise", "🤯": "surprise",
    "😨": "fear", "😰": "fear", "🤢": "disgust", "🤮": "disgust",
    
    # Keyword priorities
    "propose": "romantic", "marry": "romantic", "love": "romantic", "engagement": "romantic",
    "gym": "workout", "workout": "workout", "exercise": "workout", "training": "workout",
    "party": "party", "dance": "party", "celebrate": "party",
    "focus": "focus", "study": "focus", "work": "focus", "concentrate": "focus",
    "happy": "happy", "joy": "happy", "excited": "excited", "great": "happy", "amazing": "excited",
    "sad": "sad", "depressed": "sad", "lonely": "sad", "miserable": "sad", "unhappy": "sad",
    "angry": "angry", "mad": "angry", "furious": "angry", "hate": "angry",
    "calm": "calm", "chill": "calm", "relax": "calm",
    "neutral": "neutral", "okay": "neutral", "fine": "neutral",
}


def detect_mood_from_text(text: str) -> dict:
    text_lower = text.lower()
    
    # Check Keywords
    for keyword, mood in TEXT_MOOD_MAP.items():
        if keyword in text_lower:
            return {"mood": mood, "confidence": 90.0, "seeds": EMOTION_SEED_MAP.get(mood)}

    # Fallback to HF if available
    hf_token = os.getenv("HF_API_TOKEN")
    if hf_token:
        try:
            candidate_labels = list(EMOTION_SEED_MAP.keys())
            r = requests.post(
                "https://api-inference.huggingface.co/models/facebook/bart-large-mnli",
                headers={"Authorization": f"Bearer {hf_token}"},
                json={"inputs": text, "parameters": {"candidate_labels": candidate_labels}},
                timeout=8
            )
            if r.status_code == 200:
                data = r.json()
                mood = data["labels"][0]
                return {"mood": mood, "confidence": round(data["scores"][0]*100,1), "seeds": EMOTION_SEED_MAP[mood]}
        except: pass

    return {"mood": "neutral", "confidence": 50.0, "seeds": EMOTION_SEED_MAP["neutral"]}


_MODEL = None
_LABELS = None

def _load_model_and_labels():
    global _MODEL, _LABELS
    if _MODEL is not None: return _MODEL, _LABELS
    
    base_dir = os.path.dirname(__file__)
    model_path = os.path.join(base_dir, 'models', 'moodwave_cnn_model.h5')
    labels_path = os.path.join(base_dir, 'models', 'emotion_labels.json')
    
    try:
        with open(labels_path, 'r') as f:
            el = json.load(f)
        _LABELS = [el[str(i)] for i in range(len(el))]

        import tensorflow.keras.layers as k_layers
        class PatchedDense(k_layers.Dense):
            @classmethod
            def from_config(cls, config):
                config.pop('quantization_config', None)
                return super().from_config(config)

        _MODEL = tf.keras.models.load_model(model_path, custom_objects={'Dense': PatchedDense}, compile=False)
        return _MODEL, _LABELS
    except Exception as e:
        debug_log(f"Model Load Fail: {e}")
        return None, None


def detect_mood_from_image(image_data: str) -> dict:
    try:
        model, labels = _load_model_and_labels()
        if not model: return detect_mood_using_deepface(image_data)

        if "," in image_data: image_data = image_data.split(",")[1]
        img_bytes = base64.b64decode(image_data)
        img_full = Image.open(BytesIO(img_bytes)).convert("L") # Grayscale
        img_np = np.array(img_full.resize((48, 48))).astype('float32') / 255.0
        img_np = np.expand_dims(np.expand_dims(img_np, axis=0), axis=-1)

        preds = model.predict(img_np, verbose=0)[0]
        
        # Bias management: If confidence is low, fallback to DeepFace
        conf = float(np.max(preds))
        if conf < 0.35:
            return detect_mood_using_deepface(image_data)
            
        dom_idx = np.argmax(preds)
        mood = labels[dom_idx]
        
        return {
            "mood": mood,
            "confidence": round(conf*100, 1),
            "seeds": EMOTION_SEED_MAP.get(mood, EMOTION_SEED_MAP["neutral"]),
            "raw_emotions": {labels[i]: round(float(preds[i])*100, 1) for i in range(len(labels))}
        }
    except Exception as e:
        debug_log(f"Image Analyze Fail: {e}")
        return detect_mood_using_deepface(image_data)


def detect_mood_using_deepface(image_data: str) -> dict:
    try:
        from deepface import DeepFace
        if "," in image_data: image_data = image_data.split(",")[1]
        img_bytes = base64.b64decode(image_data)
        img_np = np.array(Image.open(BytesIO(img_bytes)).convert("RGB"))
        
        objs = DeepFace.analyze(img_np, actions=['emotion'], enforce_detection=False, silent=True)
        res = objs[0] if isinstance(objs, list) else objs
        mood = res['dominant_emotion'].lower()
        
        return {
            "mood": mood,
            "confidence": round(res['emotion'][mood], 1),
            "seeds": EMOTION_SEED_MAP.get(mood, EMOTION_SEED_MAP["neutral"]),
            "raw_emotions": res['emotion']
        }
    except Exception as e:
        debug_log(f"DeepFace Fail: {e}")
        return {"mood": "neutral", "confidence": 50.0, "seeds": EMOTION_SEED_MAP["neutral"]}
