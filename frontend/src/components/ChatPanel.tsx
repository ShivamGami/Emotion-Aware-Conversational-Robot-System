import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Mic, MicOff, Volume2, Loader2 } from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import { API_BASE_URL } from '../config';
import '../styles/Chat.css';

interface Message {
  id: string;
  sender: 'user' | 'robot';
  text: string;
  emotion?: string;
  timestamp: string;
}

const EMOTION_ICONS: Record<string, string> = {
  happy: '😊', sad: '😢', angry: '😠', fearful: '😨',
  surprised: '😲', disgust: '🤢', calm: '😌', neutral: '🤖',
};

interface ChatPanelProps {
  currentEmotion?: string;
  sessionId?: number | null;
  mode?: 'standard' | 'immersive';
}

const ChatPanel: React.FC<ChatPanelProps> = ({ currentEmotion = 'neutral', sessionId: _sessionId, mode = 'standard' }) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '0',
      sender: 'robot',
      text: '🤖 System ready. I am listening.',
      emotion: 'neutral',
      timestamp: new Date().toLocaleTimeString(),
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<any>(null);
  const user = useAuthStore((state) => state.user);
  const token = useAuthStore((state) => state.token);

  // Latest message for Subtitle mode
  const latestMessage = messages[messages.length - 1];

  // Auto-scroll to bottom
  useEffect(() => {
    if (mode === 'standard') {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, mode]);

  // Handle Spacebar for push-to-talk
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.code === 'Space' && !isListening && (document.activeElement?.tagName !== 'INPUT' && document.activeElement?.tagName !== 'TEXTAREA')) {
        e.preventDefault();
        toggleListening();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isListening]);

  // ── TTS: Speak robot text with emotion-matched voice ──
  const speak = useCallback(async (text: string, emotion: string) => {
    try {
      window.speechSynthesis.cancel();
      const resp = await fetch(`${API_BASE_URL}/api/tts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, emotion }),
      });
      const data = await resp.json();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.pitch = data.tts_settings?.pitch ?? 1;
      utterance.rate = data.tts_settings?.rate ?? 1;
      utterance.volume = data.tts_settings?.volume ?? 1;
      const voices = window.speechSynthesis.getVoices();
      const preferred = voices.find(v => v.lang.startsWith('en'));
      if (preferred) utterance.voice = preferred;
      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      window.speechSynthesis.speak(utterance);
    } catch {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      window.speechSynthesis.speak(utterance);
    }
  }, []);

  // ── Send message to /api/chat ──
  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim()) return;
    const userMsg: Message = {
      id: Date.now().toString(),
      sender: 'user',
      text,
      timestamp: new Date().toLocaleTimeString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          message: text,
          emotion: currentEmotion,
          username: user?.username || 'friend',
        }),
      });

      const data = await response.json();
      const robotText = data.response || 'I received your message!';
      const robotEmotion = data.tts_emotion || currentEmotion;

      const robotMsg: Message = {
        id: (Date.now() + 1).toString(),
        sender: 'robot',
        text: robotText,
        emotion: robotEmotion,
        timestamp: new Date().toLocaleTimeString(),
      };
      setMessages((prev) => [...prev, robotMsg]);

      // Auto-speak robot response + push emotion to ROS/M4
      speak(robotText, robotEmotion);
      pushEmotionToRobot(robotEmotion);
    } catch (err) {
      const fallbackMsg: Message = {
        id: (Date.now() + 1).toString(),
        sender: 'robot',
        text: '🔴 Backend offline. Please start the server.',
        emotion: 'neutral',
        timestamp: new Date().toLocaleTimeString(),
      };
      setMessages((prev) => [...prev, fallbackMsg]);
    } finally {
      setIsLoading(false);
    }
  }, [currentEmotion, token, user, speak]);

  // ── Push emotion to Member 4 ROS endpoint ──
  const pushEmotionToRobot = (emotion: string) => {
    fetch(`${API_BASE_URL}/api/ros/send_emotion?fused_emotion=${emotion}`, {
      method: 'POST',
    }).catch(() => {}); // silent — M4 integration, non-blocking
  };

  // ── Voice Mic Input (Web Speech API) ──
  const toggleListening = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert('Speech recognition not supported in this browser. Use Chrome.');
      return;
    }
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognitionRef.current = recognition;
    recognition.onstart = () => setIsListening(true);
    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      sendMessage(transcript);
    };
    recognition.onerror = () => setIsListening(false);
    recognition.onend = () => setIsListening(false);
    recognition.start();
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(inputValue);
  };

  // ── RENDER (Conversation Panel) ──
  return (
    <div className="chat-panel-wrapper">
      <div className="chat-messages" id="chat-messages-container">
        {messages.map((m) => (
          <div key={m.id} className={`message-row ${m.sender}`}>
            {m.sender === 'robot' && (
              <div className="robot-avatar">{EMOTION_ICONS[m.emotion || 'neutral']}</div>
            )}
            <div className={`message-bubble ${m.sender}`}>
              <p>{m.text}</p>
              <div className="message-meta">
                <span className="msg-time">{m.timestamp}</span>
                {m.sender === 'robot' && (
                  <button
                    className="speak-btn"
                    title="Speak this message"
                    onClick={() => speak(m.text, m.emotion || 'neutral')}
                  >
                    <Volume2 size={12} />
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="message-row robot">
            <div className="robot-avatar">🤖</div>
            <div className="message-bubble robot typing-indicator">
              <span /><span /><span />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {isSpeaking && (
        <div className="speaking-bar">
          <Volume2 size={14} />
          <span>Robot is speaking...</span>
          <div className="sound-wave"><span/><span/><span/><span/><span/></div>
        </div>
      )}

      <form className="chat-input-row" onSubmit={handleSubmit}>
        <div className="emotion-pill">
          {EMOTION_ICONS[currentEmotion] || '🤖'} {currentEmotion}
        </div>
        <input
          id="chat-text-input"
          type="text"
          placeholder="Type a message..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          disabled={isLoading}
          autoComplete="off"
        />
        <button
          type="button"
          className={`mic-btn ${isListening ? 'listening' : ''}`}
          onClick={toggleListening}
          title={isListening ? 'Stop listening' : 'Hold to speak'}
        >
          {isListening ? <MicOff size={18} /> : <Mic size={18} />}
        </button>
        <button type="submit" className="send-btn" disabled={isLoading || !inputValue.trim()}>
          {isLoading ? <Loader2 size={18} className="spin" /> : <Send size={18} />}
        </button>
      </form>
    </div>
  );
};

export default ChatPanel;
