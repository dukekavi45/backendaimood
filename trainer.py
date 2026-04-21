import os
import cv2
import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Dense, Dropout, Flatten
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.utils import to_categorical

# ── Mood Labels ──────────────────────────────────────────────────────────────
LABELS = ["happy", "sad", "angry", "fear", "surprise", "neutral", "disgust"]
NUM_CLASSES = len(LABELS)

def preprocess_image(image_path, target_size=(48, 48)):
    """Convert image to grayscale and resize for training."""
    img = cv2.imread(image_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img = cv2.resize(img, target_size)
    return img / 255.0

def build_mood_model():
    """Simple CNN for Emotion Detection."""
    model = Sequential([
        Conv2D(32, (3, 3), activation='relu', input_shape=(48, 48, 1)),
        MaxPooling2D((2, 2)),
        Dropout(0.25),
        
        Conv2D(64, (3, 3), activation='relu'),
        MaxPooling2D((2, 2)),
        Dropout(0.25),
        
        Flatten(),
        Dense(128, activation='relu'),
        Dropout(0.5),
        Dense(NUM_CLASSES, activation='softmax')
    ])
    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
    return model

def train_on_data(data_dir, model_path='mood_model.h5', epochs=10):
    """
    Train a model on a local directory of images.
    Data structure should be:
      data_dir/
        happy/
        sad/
        ...
    """
    if not os.path.exists(data_dir):
        print(f"Error: Data directory {data_dir} not found.")
        return

    train_datagen = ImageDataGenerator(
        rescale=1./255,
        rotation_range=10,
        width_shift_range=0.1,
        height_shift_range=0.1,
        zoom_range=0.1,
        horizontal_flip=True,
        validation_split=0.2
    )

    train_generator = train_datagen.flow_from_directory(
        data_dir,
        target_size=(48, 48),
        color_mode="grayscale",
        batch_size=32,
        class_mode='categorical',
        subset='training'
    )

    validation_generator = train_datagen.flow_from_directory(
        data_dir,
        target_size=(48, 48),
        color_mode="grayscale",
        batch_size=32,
        class_mode='categorical',
        subset='validation'
    )

    model = build_mood_model()
    model.fit(train_generator, validation_data=validation_generator, epochs=epochs)
    model.save(model_path)
    print(f"Model saved to {model_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="MoodWave Model Trainer")
    parser.add_argument("data_dir", help="Path to dataset directory")
    parser.add_argument("--model", default="mood_model.h5", help="Path to save model (default: mood_model.h5)")
    parser.add_argument("--epochs", type=int, default=10, help="Number of training epochs")
    
    args = parser.parse_args()
    
    if os.path.exists(args.data_dir):
        print(f"Starting training on {args.data_dir}...")
        train_on_data(args.data_dir, args.model, args.epochs)
    else:
        print(f"Error: Directory '{args.data_dir}' not found.")
        print("Usage: python trainer.py <data_dir> [--model mood_model.h5] [--epochs 10]")
