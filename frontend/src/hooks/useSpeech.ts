import { useState, useCallback, useRef, useEffect } from 'react';

/**
 * useSpeech — v2.1 (Bug Fix Release)
 * ------------------------------------
 * Fixes applied:
 *  1. CRITICAL: Fixed 4-5x duplicate voice outputs.
 *     Root cause: onstop → start() race condition caused cascading restarts.
 *     Fix: Use setInterval-based recorder with a single active-recording flag.
 *     Only ONE recording can be active at a time.
 *
 *  2. Audio MIME type: Changed to 'audio/webm;codecs=opus' (what browsers actually
 *     support by default). Falls back gracefully if not supported.
 *
 *  3. Added `isFetchingEmotion` ref guard — only one API call active at a time.
 *
 *  4. Voice chunk interval: 4000ms (was 3s) — more stable, fewer partial clips.
 *
 *  5. Added proper cleanup on stop to avoid memory leaks.
 */

export const useSpeech = () => {
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const recognitionRef = useRef<any>(null);

  // ── Voice monitoring state refs ───────────────────────────────────────────
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const isRecordingActiveRef = useRef(false);   // guards against duplicate recordings
  const isFetchingEmotionRef = useRef(false);   // guards against parallel API calls
  const monitoringIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Speech-to-Text (Browser Web Speech API) ──
  const startListening = useCallback((onResult: (text: string) => void) => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert('Speech Recognition not supported in this browser. Please use Chrome.');
      return;
    }

    // Cancel any existing recognition session
    if (recognitionRef.current) {
      try { recognitionRef.current.abort(); } catch (_) {}
    }

    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;
    recognition.lang = 'en-US';
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => setIsListening(true);
    recognition.onend = () => setIsListening(false);
    recognition.onerror = (event: any) => {
      console.error('Speech recognition error:', event.error);
      setIsListening(false);
    };

    recognition.onresult = (event: any) => {
      const text = event.results[0][0].transcript;
      if (text.trim()) onResult(text.trim());
    };

    recognition.start();
  }, []);

  // ── Text-to-Speech (Browser Speech Synthesis API) ──
  const speak = useCallback((
    text: string,
    emotion: string = 'neutral',
    voiceSettings: { rate: number; pitch: number } = { rate: 1, pitch: 1 },
    onEnd?: () => void
  ) => {
    if (!window.speechSynthesis) return;

    // Cancel existing speech
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = Math.max(0.5, Math.min(2.0, voiceSettings.rate || 1.0));
    utterance.pitch = Math.max(0.5, Math.min(2.0, voiceSettings.pitch || 1.0));

    // Try to find a natural voice
    const voices = window.speechSynthesis.getVoices();
    const naturalVoice = voices.find(v =>
      v.name.includes('Google') ||
      v.name.includes('Natural') ||
      v.name.includes('Samantha') ||
      v.lang === 'en-US'
    );
    if (naturalVoice) utterance.voice = naturalVoice;

    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => {
      setIsSpeaking(false);
      if (onEnd) onEnd();
    };
    utterance.onerror = () => {
      setIsSpeaking(false);
      if (onEnd) onEnd();
    };

    window.speechSynthesis.speak(utterance);
  }, []);

  const stopSpeaking = useCallback(() => {
    window.speechSynthesis.cancel();
    setIsSpeaking(false);
  }, []);

  // ── Continuous Voice Emotion Monitoring (FIXED) ───────────────────────────
  //
  // Architecture: 
  //   - One MediaRecorder, started once.
  //   - We collect chunks for CHUNK_DURATION_MS milliseconds.
  //   - At the end of each chunk window, we stop the current recording,
  //     process the blob, then restart ONLY IF no other recording is running.
  //   - isFetchingEmotion ref ensures API calls don't stack.
  //
  const CHUNK_DURATION_MS = 4000;  // 4 seconds per voice sample

  const startVoiceEmotionMonitoring = useCallback(async (
    onEmotion: (emotion: string, confidence: number) => void
  ) => {
    // Don't start if already monitoring
    if (streamRef.current) return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const startNewRecording = () => {
        // Guard: never start a new recording if one is already running
        if (isRecordingActiveRef.current) return;
        if (!streamRef.current?.active) return;

        const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
          ? 'audio/webm;codecs=opus'
          : MediaRecorder.isTypeSupported('audio/webm')
            ? 'audio/webm'
            : '';

        const recorder = mimeType
          ? new MediaRecorder(stream, { mimeType })
          : new MediaRecorder(stream);

        mediaRecorderRef.current = recorder;
        chunksRef.current = [];
        isRecordingActiveRef.current = true;

        recorder.ondataavailable = (e) => {
          if (e.data && e.data.size > 0) {
            chunksRef.current.push(e.data);
          }
        };

        recorder.onstop = async () => {
          isRecordingActiveRef.current = false;  // Release the guard
          const chunks = chunksRef.current.slice();
          chunksRef.current = [];

          if (chunks.length === 0) return;

          // Guard: skip API call if one is already in progress
          if (isFetchingEmotionRef.current) return;

          const blob = new Blob(chunks, { type: recorder.mimeType || 'audio/webm' });

          // Need at least 2KB of audio to be meaningful
          if (blob.size < 2048) return;

          isFetchingEmotionRef.current = true;
          try {
            const reader = new FileReader();
            reader.readAsDataURL(blob);
            reader.onloadend = async () => {
              const base64Audio = reader.result as string;
              try {
                const resp = await fetch('http://localhost:8000/api/detect/voice', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ audio_base64: base64Audio }),
                });
                if (resp.ok) {
                  const data = await resp.json();
                  if (data.emotion && data.confidence > 0.1) {
                    onEmotion(data.emotion, data.confidence);
                  }
                }
              } catch (err) {
                // Silently ignore — network error or backend not reachable
              } finally {
                isFetchingEmotionRef.current = false;
              }
            };
          } catch {
            isFetchingEmotionRef.current = false;
          }
        };

        recorder.start();

        // Stop after CHUNK_DURATION_MS to process the audio
        setTimeout(() => {
          if (recorder.state === 'recording') {
            recorder.stop();
          } else {
            isRecordingActiveRef.current = false;
          }
        }, CHUNK_DURATION_MS);
      };

      // Start immediately, then repeat every (CHUNK_DURATION_MS + buffer)
      startNewRecording();
      monitoringIntervalRef.current = setInterval(() => {
        startNewRecording();
      }, CHUNK_DURATION_MS + 500);  // +500ms buffer so onstop fully completes

    } catch (err) {
      console.error('Failed to start voice monitoring:', err);
    }
  }, []);

  const stopVoiceMonitoring = useCallback(() => {
    if (monitoringIntervalRef.current) {
      clearInterval(monitoringIntervalRef.current);
      monitoringIntervalRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      try { mediaRecorderRef.current.stop(); } catch (_) {}
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
    isRecordingActiveRef.current = false;
    isFetchingEmotionRef.current = false;
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopVoiceMonitoring();
      window.speechSynthesis?.cancel();
    };
  }, [stopVoiceMonitoring]);

  return {
    isListening,
    isSpeaking,
    startListening,
    speak,
    stopSpeaking,
    startVoiceEmotionMonitoring,
    stopVoiceMonitoring,
  };
};
