"""
Task 2.8 - Multimodal Emotion Fusion
Combines face emotion (from Member 1 / DeepFace) and voice emotion (from our trained RAVDESS model)
using adaptive weighted confidence combination.

For Member 1 integration:
  - face_emotion input should come from /api/detect_face_emotion endpoint response
  - Expected format: {"emotion": "happy", "confidence": 0.87}

For Member 4 / ROS2 output:
  - fused result is returned and also stored as last_fused_emotion for /api/ros/send_emotion
"""

# Emotion-to-ROS2 behavior mapping for Member 4
EMOTION_ROS_BEHAVIORS = {
    "happy":     {"animation": "dance",       "speed": 1.2, "color": "#ffd700"},
    "sad":       {"animation": "head_down",   "speed": 0.7, "color": "#4169e1"},
    "angry":     {"animation": "stomp",       "speed": 1.5, "color": "#ff4444"},
    "fearful":   {"animation": "cower",       "speed": 0.9, "color": "#9400d3"},
    "surprised": {"animation": "jump_back",   "speed": 1.3, "color": "#ff8c00"},
    "disgust":   {"animation": "turn_away",   "speed": 0.8, "color": "#556b2f"},
    "calm":      {"animation": "idle_breath", "speed": 1.0, "color": "#00ced1"},
    "neutral":   {"animation": "idle_breath", "speed": 1.0, "color": "#ffffff"},
}

# Normalise confidence values from various detector outputs
def _normalize_confidence(conf):
    if conf is None:
        return 0.5
    return max(0.0, min(1.0, float(conf)))

def fuse_emotions(face_emotion: str, face_confidence: float,
                  voice_emotion: str, voice_confidence: float) -> dict:
    """
    Weighted combination: higher-confidence source wins more influence.
    Returns the fused emotion label + ROS2 behavior command.
    """
    face_conf  = _normalize_confidence(face_confidence)
    voice_conf = _normalize_confidence(voice_confidence)

    total = face_conf + voice_conf
    if total == 0:
        total = 1.0

    face_weight  = face_conf  / total
    voice_weight = voice_conf / total

    # If both agree, trivially return either
    if face_emotion == voice_emotion:
        fused = face_emotion
    elif face_weight >= voice_weight:
        fused = face_emotion
    else:
        fused = voice_emotion

    ros_behavior = EMOTION_ROS_BEHAVIORS.get(fused, EMOTION_ROS_BEHAVIORS["neutral"])

    return {
        "fused_emotion":    fused,
        "face_emotion":     face_emotion,
        "face_confidence":  face_conf,
        "voice_emotion":    voice_emotion,
        "voice_confidence": voice_conf,
        "face_weight":      round(face_weight, 3),
        "voice_weight":     round(voice_weight, 3),
        "ros_behavior":     ros_behavior,
    }
