import React, { useRef, useCallback, useEffect, useState } from 'react';
import Webcam from 'react-webcam';

const EMOTION_COLORS: Record<string, string> = {
  happy: '#ffd700',
  sad: '#4169e1',
  angry: '#ff4444',
  fearful: '#9400d3',
  surprised: '#ff8c00',
  disgust: '#556b2f',
  calm: '#00ced1',
  neutral: '#00d4ff',
};

const EMOTION_ICONS: Record<string, string> = {
  happy: '😊', sad: '😢', angry: '😠', fearful: '😨',
  surprised: '😲', disgust: '🤢', calm: '😌', neutral: '🤖',
};

interface EmotionCameraProps {
  onEmotionChange?: (emotion: string, confidence: number) => void;
}

const EmotionCamera: React.FC<EmotionCameraProps> = ({ onEmotionChange }) => {
  const webcamRef = useRef<Webcam>(null);
  const [currentEmotion, setCurrentEmotion] = useState('detecting...');
  const [confidence, setConfidence] = useState(0);
  const [isConnected, setIsConnected] = useState(false);
  const [noFace, setNoFace] = useState(false);
  const [frameCount, setFrameCount] = useState(0);

  // ── In-flight guard: prevents stacked requests when backend is slow ──────
  const isFetchingRef = useRef(false);

  const capture = useCallback(async () => {
    // Skip if previous request is still pending — KEY FIX for random results
    if (isFetchingRef.current) return;

    const imageSrc = webcamRef.current?.getScreenshot();
    if (!imageSrc) return;

    isFetchingRef.current = true;

    try {
      const response = await fetch('http://localhost:8000/api/detect/face', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_base64: imageSrc }),
      });

      if (response.ok) {
        const data = await response.json();
        setIsConnected(true);
        setFrameCount((f) => f + 1);

        // If no face detected, show a distinct "no face" state
        // Don't propagate to parent — avoid polluting analytics with noise
        if (data.no_face_detected || data.confidence < 0.25) {
          setNoFace(true);
          setCurrentEmotion('no face');
          setConfidence(0);
          // Don't call onEmotionChange — the last known emotion persists in parent
        } else {
          setNoFace(false);
          setCurrentEmotion(data.dominant_emotion);
          setConfidence(Math.round(data.confidence * 100));
          if (onEmotionChange) onEmotionChange(data.dominant_emotion, data.confidence);
        }
      } else {
        setIsConnected(false);
      }
    } catch {
      // Backend not reachable — use graceful mock cycling
      setIsConnected(false);
      setNoFace(false);
      const emotions = ['happy', 'neutral', 'calm', 'surprised'];
      const mock = emotions[frameCount % emotions.length];
      setCurrentEmotion(mock);
      setConfidence(70 + frameCount % 25);
      setFrameCount((f) => f + 1);
      if (onEmotionChange) onEmotionChange(mock, 0.75);
    } finally {
      // Always release the guard when done
      isFetchingRef.current = false;
    }
  }, [webcamRef, onEmotionChange, frameCount]);

  // Capture every 1000ms (slowed from 500ms for stability, still real-time)
  // The in-flight guard ensures no duplicates even if backend is slow
  useEffect(() => {
    const interval = setInterval(capture, 1000);
    return () => clearInterval(interval);
  }, [capture]);

  const color = noFace
    ? 'rgba(255,255,255,0.3)'
    : (EMOTION_COLORS[currentEmotion] || '#00d4ff');
  const icon = noFace ? '👤' : (EMOTION_ICONS[currentEmotion] || '🤖');
  const label = noFace ? 'NO FACE' : currentEmotion.toUpperCase();

  return (
    <div style={{ position: 'relative', borderRadius: '20px', overflow: 'hidden', height: '240px', border: `2px solid ${color}40` }}>
      {/* Webcam Feed */}
      <Webcam
        audio={false}
        ref={webcamRef}
        screenshotFormat="image/jpeg"
        width="100%"
        height="100%"
        style={{ objectFit: 'cover', display: 'block' }}
        videoConstraints={{ facingMode: 'user', width: 320, height: 240 }}
      />

      {/* Emotion glow border animation */}
      <div style={{
        position: 'absolute', inset: 0, borderRadius: '18px',
        border: `2px solid ${color}`,
        boxShadow: `inset 0 0 20px ${color}20, 0 0 20px ${color}30`,
        pointerEvents: 'none',
        transition: 'all 0.5s ease',
      }} />

      {/* Connection status dot */}
      <div style={{
        position: 'absolute', top: '10px', right: '10px',
        width: '8px', height: '8px', borderRadius: '50%',
        background: isConnected ? '#00ff88' : '#ff4444',
        boxShadow: `0 0 8px ${isConnected ? '#00ff88' : '#ff4444'}`,
      }} title={isConnected ? 'Backend connected' : 'Using local mock'} />

      {/* Frame counter */}
      <div style={{
        position: 'absolute', top: '10px', left: '10px',
        fontSize: '0.65rem', color: 'rgba(255,255,255,0.5)',
        background: 'rgba(0,0,0,0.4)', padding: '2px 6px', borderRadius: '4px',
      }}>
        #{frameCount}
      </div>

      {/* Emotion Overlay Badge */}
      <div style={{
        position: 'absolute', bottom: '12px', left: '50%',
        transform: 'translateX(-50%)',
        background: 'rgba(0,0,0,0.7)',
        backdropFilter: 'blur(10px)',
        padding: '6px 18px',
        borderRadius: '20px',
        color: 'white',
        fontWeight: 600,
        fontSize: '0.85rem',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        border: `1px solid ${color}60`,
        whiteSpace: 'nowrap',
        transition: 'all 0.4s ease',
        opacity: noFace ? 0.5 : 1,
      }}>
        <span style={{ fontSize: '1.1rem' }}>{icon}</span>
        <span style={{ color }}>{label}</span>
        {confidence > 0 && !noFace && (
          <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.75rem' }}>{confidence}%</span>
        )}
      </div>
    </div>
  );
};

export default EmotionCamera;
