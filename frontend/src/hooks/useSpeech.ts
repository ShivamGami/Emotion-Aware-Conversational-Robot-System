import { useState, useCallback, useRef, useEffect } from 'react';
import { API_BASE_URL } from '../config';

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
 *
 *  6. NEW (v2.2): Added pure-JS WAV encoder. This sends WAV to the backend,
 *     which bypasses the need for FFmpeg (backend soundfile handles WAV natively).
 */

// Helper: Minimal WAV encoder for mono PCM data
const encodeWAV = (samples: Float32Array, sampleRate: number): Blob => {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const writeString = (offset: number, s: string) => {
    for (let i = 0; i < s.length; i++) view.setUint8(offset + i, s.charCodeAt(i));
  };
  writeString(0, 'RIFF');
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(8, 'WAVE');
  writeString(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // Mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true); // Byte rate
  view.setUint16(32, 2, true); // Block align
  view.setUint16(34, 16, true); // Bits per sample
  writeString(36, 'data');
  view.setUint32(40, samples.length * 2, true);
  let offset = 44;
  for (let i = 0; i < samples.length; i++, offset += 2) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
  }
  return new Blob([view], { type: 'audio/wav' });
};


export const useSpeech = () => {
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const recognitionRef = useRef<any>(null);

  // ── Voice monitoring state refs ───────────────────────────────────────────
  const streamRef = useRef<MediaStream | null>(null);

  const isRecordingActiveRef = useRef(false);   // guards against duplicate recordings
  const isFetchingEmotionRef = useRef(false);   // guards against parallel API calls
  const monitoringIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const pcmDataRef = useRef<Float32Array[]>([]);
  const recognitionTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const currentUtteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
  const [availableVoices, setAvailableVoices] = useState<SpeechSynthesisVoice[]>([]);




  // ── Speech-to-Text (Browser Web Speech API) ──
  const startListening = useCallback((onResult: (text: string) => void, onInterim?: (text: string) => void) => {
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
    recognition.lang = 'hi-IN'; // Default to Hindi + Hinglish + English support
    recognition.continuous = true; // Support continuous listening gracefully
    recognition.interimResults = true;  // Show live typing as user speaks
    recognition.maxAlternatives = 1;

    let silenceTimer: ReturnType<typeof setTimeout> | null = null;
    let lastInterim = '';
    let manualStop = false;

    // Coordination: stop emotion monitoring if active to free up mic
    const wasMonitoring = !!audioContextRef.current;
    if (wasMonitoring) {
      console.log('--- Pausing Emotion Monitoring for STT ---');
      stopVoiceMonitoring();
    }

    recognition.onstart = () => {
      console.log('--- Speech Recognition Started ---');
      setIsListening(true);
      manualStop = false;
    };

    recognition.onend = () => {
      console.log('--- Speech Recognition Ended ---');
      if (!manualStop) {
        // Auto-restart delay prevents Chrome crash loop
        setTimeout(() => {
          try { recognition.start(); } catch (_) {}
        }, 800);
      } else {
        setIsListening(false);
      }
    };

    recognition.onerror = (event: any) => {
      console.error('Speech recognition error:', event.error);
      setIsListening(false);
      // Auto-retry on network errors
      if (event.error === 'network' || event.error === 'aborted') {
        setTimeout(() => {
          try { recognition.start(); } catch (_) {}
        }, 500);
      }
    };

    recognition.onresult = (event: any) => {
      const result = event.results[event.results.length - 1];
      const text = result[0].transcript.trim();

      if (!text) return; // Ignore pure noise

      if (result.isFinal) {
        if (silenceTimer) clearTimeout(silenceTimer);
        console.log('--- STT Final Result:', text);
        if (text.length > 1) {
            manualStop = true; // Stop listening to process the command
            try { recognition.stop(); } catch (_) {} 
            onResult(text);
        }
      } else {
        lastInterim = text;
        if (onInterim) onInterim(text);
        
        // BUG FIX: Reduce delay between speaking and processing.
        // Google WebSpeech waits 2-5 secs of silence before `isFinal`. 
        // We force-process if there's an interim result and 2500ms silence.
        if (silenceTimer) clearTimeout(silenceTimer);
        silenceTimer = setTimeout(() => {
            if (lastInterim && lastInterim.length > 1) {
                console.log('--- STT Silence Detected -> Forcing Final:', lastInterim);
                manualStop = true;
                try { recognition.stop(); } catch (_) {}
                onResult(lastInterim);
                lastInterim = '';
            }
        }, 2500);
      }
    };

    recognition.start();
  }, []);

  // Load and cache voices for faster switching
  useEffect(() => {
    if (!window.speechSynthesis) return;

    const loadVoices = () => {
      const v = window.speechSynthesis.getVoices();
      if (v.length > 0) {
        setAvailableVoices(v);
        console.log('--- Voices Pre-loaded:', v.length);
      }
    };

    loadVoices();
    if (window.speechSynthesis.onvoiceschanged !== undefined) {
      window.speechSynthesis.onvoiceschanged = loadVoices;
    }
  }, []);

  // ── Text-to-Speech (Browser Speech Synthesis API) ──
  const speak = useCallback((
    text: string,
    emotion: string = 'neutral',
    voiceSettings: { rate: number; pitch: number } = { rate: 1, pitch: 1 },
    onEnd?: () => void
  ) => {
    if (!window.speechSynthesis) return;

    // IMPORTANT: Cancel existing speech and CLEAR ref to prevent collision
    window.speechSynthesis.cancel();
    currentUtteranceRef.current = null;

    // Sanitize text: Remove markdown or extra spaces that could confuse TTS
    const cleanText = text.replace(/[*_#`]/g, '').trim();
    if (!cleanText) return;

    const utterance = new SpeechSynthesisUtterance(cleanText);
    
    // HOLD REFERENCE: Critical fix for Chrome garbage collection bug
    currentUtteranceRef.current = utterance;
    
    // --- Multilingual Detection ---
    const isHindi = /[\u0900-\u097F]/.test(cleanText);
    if (isHindi) {
      utterance.lang = 'hi-IN';
    } else {
      utterance.lang = 'en-US';
    }

    // --- Robot Voice Effect ---
    const robotRate = 0.95; 
    const robotPitch = 0.9; 
    utterance.rate = Math.max(0.5, Math.min(2.0, (voiceSettings.rate || 1.0) * robotRate));
    utterance.pitch = Math.max(0.5, Math.min(2.0, (voiceSettings.pitch || 1.0) * robotPitch));

    // --- Voice Selection ---
    // Use pre-loaded voices first, fallback to fresh call if state is empty
    const voices = availableVoices.length > 0 ? availableVoices : window.speechSynthesis.getVoices();

    let selectedVoice = null;
    if (isHindi) {
      selectedVoice = voices.find(v => v.lang.startsWith('hi') || v.name.includes('India'));
    }

    if (!selectedVoice) {
      selectedVoice = voices.find(v => 
        (v.lang === 'en-US' && (v.name.includes('Google') || v.name.includes('Natural') || v.name.includes('Samantha'))) ||
        v.name.toLowerCase().includes('robot') || 
        v.name.includes('Zira')
      );
    }

    if (selectedVoice) {
      utterance.voice = selectedVoice;
      console.log('--- Speaking with Voice:', selectedVoice.name, '[', selectedVoice.lang, ']');
    }

    utterance.onstart = () => setIsSpeaking(true);
    
    utterance.onend = () => {
      console.log('--- Speech Finished Successfully ---');
      setIsSpeaking(false);
      currentUtteranceRef.current = null;
      if (onEnd) onEnd();
    };

    utterance.onerror = (e) => {
      if (e.error === 'interrupted') {
        console.log('--- Speech interrupted by new request ---');
      } else {
        console.error('TTS Terminal Error:', e);
      }
      setIsSpeaking(false);
      currentUtteranceRef.current = null;
      if (onEnd) onEnd();
    };

    window.speechSynthesis.speak(utterance);
  }, [availableVoices]);

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


  const startVoiceEmotionMonitoring = useCallback(async (
    onEmotion: (emotion: string, confidence: number) => void
  ) => {
    // Don't start if already monitoring
    if (audioContextRef.current) return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const audioCtx = new AudioContext();
      audioContextRef.current = audioCtx;
      const source = audioCtx.createMediaStreamSource(stream);
      const processor = audioCtx.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      pcmDataRef.current = [];
      isRecordingActiveRef.current = true;

      processor.onaudioprocess = (e) => {
        if (!isRecordingActiveRef.current) return;
        const input = e.inputBuffer.getChannelData(0);
        pcmDataRef.current.push(new Float32Array(input));
      };

      source.connect(processor);
      processor.connect(audioCtx.destination);

      const processChunk = async () => {
        if (pcmDataRef.current.length === 0 || isFetchingEmotionRef.current) return;

        // Flatten chunks
        const totalLength = pcmDataRef.current.reduce((acc, curr) => acc + curr.length, 0);
        const flattened = new Float32Array(totalLength);
        let offset = 0;
        for (const chunk of pcmDataRef.current) {
          flattened.set(chunk, offset);
          offset += chunk.length;
        }
        pcmDataRef.current = [];

        // Encode to WAV (Native support in soundfile/backend)
        const wavBlob = encodeWAV(flattened, audioCtx.sampleRate);
        if (wavBlob.size < 2048) return;

        isFetchingEmotionRef.current = true;
        try {
          const reader = new FileReader();
          reader.readAsDataURL(wavBlob);
          reader.onloadend = async () => {
            const base64Audio = reader.result as string;
            try {
              const resp = await fetch(`${API_BASE_URL}/api/detect/voice`, {
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
              console.error('Emotion detection API error:', err);
            } finally {
              isFetchingEmotionRef.current = false;
            }
          };
        } catch {
          isFetchingEmotionRef.current = false;
        }
      };

      // Interval to send to backend
      monitoringIntervalRef.current = setInterval(processChunk, 4000);

    } catch (err) {
      console.error('Failed to start voice monitoring:', err);
    }
  }, []);

  const stopVoiceMonitoring = useCallback(() => {
    isRecordingActiveRef.current = false;
    if (monitoringIntervalRef.current) {
      clearInterval(monitoringIntervalRef.current);
      monitoringIntervalRef.current = null;
    }
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
    isFetchingEmotionRef.current = false;
    pcmDataRef.current = [];
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
