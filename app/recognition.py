"""
Smart Attendance System — Face Recognition (Vision Layer)
==========================================================
Face detection, encoding, matching, and registration using
the face_recognition library with HOG-based detection.

Matching uses **cosine similarity** on normalised 128-d embeddings:
    similarity = dot(a, b) / (||a|| * ||b||)
    1.0 = identical   →   0.0 = completely different
"""

import os
import pickle
import logging
import numpy as np
import face_recognition

import config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Embedding Storage
# ---------------------------------------------------------------------------

def load_embeddings():
    """
    Load known face encodings from pickle file.

    Returns:
        dict: {"ids": [...], "names": [...], "encodings": [...]}
    """
    if not os.path.exists(config.EMBEDDINGS_FILE):
        logger.info("No embeddings file found — starting fresh")
        return {"ids": [], "names": [], "encodings": []}

    try:
        with open(config.EMBEDDINGS_FILE, "rb") as f:
            data = pickle.load(f)
        logger.info(f"Loaded {len(data['names'])} user(s) from embeddings")
        return data
    except Exception as e:
        logger.error(f"Failed to load embeddings: {e}")
        return {"ids": [], "names": [], "encodings": []}


def save_embeddings(data):
    """
    Save face encodings to pickle file.

    Args:
        data: dict with keys "ids", "names", "encodings"
    """
    try:
        with open(config.EMBEDDINGS_FILE, "wb") as f:
            pickle.dump(data, f)
        logger.info(f"Saved {len(data['names'])} encoding(s) to disk")
    except Exception as e:
        logger.error(f"Failed to save embeddings: {e}")


# ---------------------------------------------------------------------------
# Cosine Similarity
# ---------------------------------------------------------------------------

def cosine_similarity(a, b):
    """
    Compute cosine similarity between two vectors.

    Args:
        a: numpy array (128-d face encoding)
        b: numpy array (128-d face encoding)

    Returns:
        float: similarity score from 0.0 (orthogonal) to 1.0 (identical)
    """
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(dot_product / (norm_a * norm_b))


def cosine_similarities(known_encodings, face_encoding):
    """
    Compute cosine similarity of a face encoding against a list of
    known encodings.

    Args:
        known_encodings: list of 128-d numpy arrays
        face_encoding:   single 128-d numpy array

    Returns:
        numpy array of similarity scores (0.0–1.0)
    """
    if len(known_encodings) == 0:
        return np.array([])

    known = np.array(known_encodings)
    # Normalise both sides
    known_norms = np.linalg.norm(known, axis=1, keepdims=True)
    face_norm = np.linalg.norm(face_encoding)

    if face_norm == 0:
        return np.zeros(len(known_encodings))

    # Vectorised dot product / (||a|| * ||b||)
    similarities = np.dot(known, face_encoding) / (known_norms.flatten() * face_norm)
    return similarities


# ---------------------------------------------------------------------------
# Face Detection & Encoding
# ---------------------------------------------------------------------------

def detect_and_encode(frame):
    """
    Detect faces in a frame and compute their 128-d encodings.

    Args:
        frame: BGR image (numpy array from OpenCV)

    Returns:
        tuple: (face_locations, face_encodings)
            - face_locations: list of (top, right, bottom, left) tuples
            - face_encodings: list of 128-d numpy arrays
    """
    # Convert BGR (OpenCV) to RGB (face_recognition) and ensure contiguous memory
    rgb_frame = np.ascontiguousarray(frame[:, :, ::-1])

    # Detect face locations using HOG (fast, CPU-optimized)
    face_locations = face_recognition.face_locations(
        rgb_frame,
        model=config.FACE_DETECTION_MODEL
    )

    # Limit number of faces for performance
    if len(face_locations) > config.MAX_FACES_PER_FRAME:
        face_locations = face_locations[:config.MAX_FACES_PER_FRAME]

    # Compute 128-dimensional face encodings
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

    return face_locations, face_encodings


# ---------------------------------------------------------------------------
# Face Recognition (Matching via Cosine Similarity)
# ---------------------------------------------------------------------------

def recognize_faces(frame, known_data):
    """
    Detect and recognize faces in a frame against known encodings
    using cosine similarity.

    Args:
        frame: BGR image (numpy array)
        known_data: dict from load_embeddings()

    Returns:
        list of dicts: [
            {
                "name": str,
                "id": str,
                "confidence": float (0.0 to 1.0),
                "bbox": (top, right, bottom, left)
            },
            ...
        ]
    """
    face_locations, face_encodings = detect_and_encode(frame)
    results = []

    if not face_encodings:
        return results

    known_encodings = known_data.get("encodings", [])
    known_names = known_data.get("names", [])
    known_ids = known_data.get("ids", [])

    for encoding, location in zip(face_encodings, face_locations):
        name = "Unknown"
        user_id = "unknown"
        confidence = 0.0

        if known_encodings:
            # Compute cosine similarity to all known faces
            similarities = cosine_similarities(known_encodings, encoding)
            best_match_idx = np.argmax(similarities)
            best_similarity = similarities[best_match_idx]

            # Confidence is the raw cosine similarity (0.0–1.0)
            confidence = max(0.0, float(best_similarity))

            # Check if above cosine similarity threshold
            if best_similarity >= config.COSINE_THRESHOLD:
                name = known_names[best_match_idx]
                user_id = known_ids[best_match_idx]

        results.append({
            "name": name,
            "id": user_id,
            "confidence": confidence,
            "bbox": location
        })

    return results


# ---------------------------------------------------------------------------
# Face Registration
# ---------------------------------------------------------------------------

def register_face(name, user_id, frames):
    """
    Register a new face by encoding multiple sample frames.

    Args:
        name: Person's name
        user_id: Unique identifier
        frames: List of BGR images containing the person's face

    Returns:
        bool: True if registration successful, False otherwise
    """
    all_encodings = []

    for i, frame in enumerate(frames):
        rgb_frame = np.ascontiguousarray(frame[:, :, ::-1])
        locations = face_recognition.face_locations(
            rgb_frame, model=config.FACE_DETECTION_MODEL
        )

        if not locations:
            logger.warning(f"No face detected in sample {i + 1}")
            continue

        # Use the first (largest) face found
        encodings = face_recognition.face_encodings(rgb_frame, [locations[0]])
        if encodings:
            all_encodings.append(encodings[0])
            logger.info(f"Encoded sample {i + 1}/{len(frames)}")

    if not all_encodings:
        logger.error("No valid face encodings obtained — registration failed")
        return False

    # Average the encodings for a more robust representation
    avg_encoding = np.mean(all_encodings, axis=0)

    # Load existing data and append
    data = load_embeddings()
    data["ids"].append(user_id)
    data["names"].append(name)
    data["encodings"].append(avg_encoding)

    save_embeddings(data)
    logger.info(f"Registered face for: {name} ({user_id}) with {len(all_encodings)} samples")
    return True
