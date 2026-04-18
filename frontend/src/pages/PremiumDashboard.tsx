import React, { useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { useSpeech } from '../hooks/useSpeech';
import { API_BASE_URL } from '../config';
import EmotionCamera from '../components/EmotionCamera';
import SubtitleOverlay from '../components/SubtitleOverlay';
import RobotScene3D from '../components/RobotScene3D';
import MemoryTimeline from '../components/MemoryTimeline';
import AnalyticsDashboard from '../components/AnalyticsDashboard';
import ChatPanel from '../components/ChatPanel';
import '../styles/PremiumDashboard.css';
import { LogOut, User, BarChart2, Brain, Home, Mic, MicOff, Settings, Network } from 'lucide-react';

type ActiveTab = 'dashboard' | 'analytics' | 'memories' | 'profile';

const PremiumDashboard: React.FC = () => {
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const navigate = useNavigate();
  const { isListening, isSpeaking, startListening, speak, startVoiceEmotionMonitoring, stopVoiceMonitoring } = useSpeech();

  // ── State ──
  const [currentEmotion, setCurrentEmotion] = useState('neutral');
  const [faceConfidence, setFaceConfidence] = useState(0.75);
  const [voiceEmotion, setVoiceEmotion] = useState('neutral');
  const [voiceConfidence, setVoiceConfidence] = useState(0.65);
  const [activeTab, setActiveTab] = useState<ActiveTab>('dashboard');
  const [systemStatus, setSystemStatus] = useState<string | null>(null);

  // ── Subtitle State (Dual Speaker) ──
  const [subtitle, setSubtitle] = useState({ text: '', speaker: 'EmoBot' as string, isVisible: false, isThinking: false });
  const subtitleTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showSubtitle = (text: string, speaker: string, autoHideMs = 0) => {
    if (subtitleTimeoutRef.current) clearTimeout(subtitleTimeoutRef.current);
    setSubtitle({ text, speaker, isVisible: true, isThinking: false });
    if (autoHideMs > 0) {
      subtitleTimeoutRef.current = setTimeout(() => {
        setSubtitle(s => ({ ...s, isVisible: false }));
      }, autoHideMs);
    }
  };

  // ── Orchestration: The Brain ──
  const processConversation = useCallback(async (userText: string) => {
    try {
      // 1. Show USER subtitle
      showSubtitle(userText, 'You');

      // 2. After 1.5s, show "thinking" animation
      setTimeout(() => {
        setSubtitle({ text: '', speaker: 'EmoBot', isVisible: true, isThinking: true });
      }, 1500);

      setSystemStatus('AI Thinking...');
      stopVoiceMonitoring();

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 15000);

      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ text: userText, emotion: currentEmotion }),
        signal: controller.signal
      });
      clearTimeout(timeoutId);

      if (!response.ok) {
        setSystemStatus(`Error: ${response.status}`);
        setTimeout(() => setSystemStatus(null), 3000);
        setSubtitle(s => ({ ...s, isVisible: false }));
        return;
      }

      const data = await response.json();
      setSystemStatus(null);

      // 3. Show ROBOT subtitle
      showSubtitle(data.response, 'EmoBot');

      // 4. Notify Bridge
      await fetch(`${API_BASE_URL}/api/bridge/speech_state`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_speaking: true, text: data.response }),
      }).catch(() => {});

      // 5. Speak with TTS
      speak(data.response, data.speak_with_emotion, data.voice_settings, async () => {
        // Auto-hide subtitle 2s after speech ends
        if (subtitleTimeoutRef.current) clearTimeout(subtitleTimeoutRef.current);
        subtitleTimeoutRef.current = setTimeout(() => {
          setSubtitle(s => ({ ...s, isVisible: false }));
        }, 2000);

        await fetch(`${API_BASE_URL}/api/bridge/speech_state`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ is_speaking: false }),
        }).catch(() => {});
      });

    } catch (err: any) {
      if (err.name === 'AbortError') {
        setSystemStatus('AI Timeout');
      } else {
        setSystemStatus('Error');
      }
      setTimeout(() => setSystemStatus(null), 3000);
      setSubtitle(s => ({ ...s, isVisible: false }));
    }
  }, [currentEmotion, speak, stopVoiceMonitoring]);

  // ── Continuous Voice Emotion Monitoring ──
  React.useEffect(() => {
    startVoiceEmotionMonitoring((emotion, confidence) => {
      setVoiceEmotion(emotion);
      setVoiceConfidence(confidence);
    });
  }, [startVoiceEmotionMonitoring]);

  const handleStartInteraction = () => {
    startListening(
      (text) => {
        // Final result — process the conversation
        processConversation(text);
      },
      (interimText) => {
        // Interim result — show live typing as user speaks
        showSubtitle(interimText + '...', 'You');
      }
    );
  };

  const handleEmotionChange = (emotion: string, confidence: number) => {
    setCurrentEmotion(emotion);
    setFaceConfidence(confidence);
  };

  const handleLogout = () => { logout(); navigate('/login'); };

  return (
    <div className="premium-container">
      {/* ── Top Navigation ── */}
      <nav className="premium-nav">
        <div className="nav-brand">
          <span className="brand-dot" />
          EmoBot OS
        </div>
        <div className="nav-links">
          {([
            { id: 'dashboard', label: 'Dashboard', icon: <Home size={15}/> },
            { id: 'analytics', label: 'Analytics', icon: <BarChart2 size={15}/> },
            { id: 'memories', label: 'Memories', icon: <Brain size={15}/> },
            { id: 'profile', label: 'Profile', icon: <User size={15}/> },
          ] as { id: ActiveTab; label: string; icon: React.ReactNode }[]).map(tab => (
            <button
              key={tab.id}
              className={`nav-link ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>
        <div className="nav-actions">
          <button className="icon-btn" title="System Tree"><Network size={16} /></button>
          <div className="emotion-live-badge" data-emotion={currentEmotion}>
            <span className="pulse-dot" />
            {currentEmotion.toUpperCase()}
          </div>
          <button className="icon-btn logout-btn" onClick={handleLogout} title="Logout">
            <LogOut size={16} />
          </button>
        </div>
      </nav>

      {/* ═══════════ DASHBOARD TAB (IMMERSIVE STUDIO) ═══════════ */}
      {activeTab === 'dashboard' && (
        <div className="immersive-studio-container">
          <div className="immersive-background">
            <RobotScene3D emotion={currentEmotion} />
          </div>

          {/* Dual-Speaker Subtitles */}
          <SubtitleOverlay 
            text={subtitle.text}
            speaker={subtitle.speaker}
            isVisible={subtitle.isVisible}
            emotion={currentEmotion}
            isThinking={subtitle.isThinking}
          />

          {/* Left: Webcam (Vision Panel) */}
          <div className="floating-panel top-left animate-slide-in-left">
            <div className="glass-window">
              <div className="window-header">
                <span>• VISION</span>
                <div className="window-close">×</div>
              </div>
              <div className="webcam-mini">
                <EmotionCamera onEmotionChange={handleEmotionChange} />
              </div>
            </div>
          </div>


          {/* Master Control: Center Mic Button Rings */}
          <div className="floating-panel bottom-center">
            {systemStatus && (
              <div className="system-status-pill animate-fade-in" style={{ position: 'absolute', top: '-40px' }}>
                {systemStatus}
              </div>
            )}
            <div className="mic-rings-wrapper">
               {/* 3 Rings simulating the concentric pulses. Using inline styles for simplicity here, 
                   or handled entirely by CSS in RobotScene3D if it's the 3D ground. We will put the 
                   HTML rings here. */}
               <div className="mic-ring" style={{ width: '400px', height: '140px', bottom: '-70px', opacity: 0.1 }} />
               <div className="mic-ring" style={{ width: '280px', height: '100px', bottom: '-50px', opacity: 0.3 }} />
               <div className="mic-ring" style={{ width: '160px', height: '60px', bottom: '-30px', opacity: 0.6 }} />
               
               <button 
                className={`mic-trigger-btn ${isListening ? 'listening' : ''} ${isSpeaking ? 'speaking' : ''}`}
                onClick={handleStartInteraction}
                disabled={isSpeaking}
               >
                 {isListening ? <MicOff size={24} color={isListening ? '#ff0096' : 'white'} /> : <Mic size={24} />}
               </button>
            </div>
            <div className="click-to-speak-label">CLICK TO SPEAK</div>
          </div>

          {/* Greeting: Bottom Left */}
          <div className="studio-greeting">
            <h2 className="studio-title">
              Hello, <span className="gradient-name">{user?.username || 'sarah'}</span>
            </h2>
            <p className="studio-sub">Emotion-Aware OS v3.0</p>
          </div>

          {/* Stats Badge: Bottom Right */}
          <div className="bottom-right-stats">
            <div className="stat-part bot">
               🤖 {currentEmotion}
            </div>
            <div className="stat-part face">
               FACE {faceConfidence}%
            </div>
            <div className="stat-part voice">
               VOICE {Math.round(voiceConfidence * 100)}%
            </div>
          </div>
        </div>
      )}

      {/* ═══════════ ANALYTICS TAB ═══════════ */}
      {activeTab === 'analytics' && (
        <div className="tab-content-full">
          <div className="tab-header">
            <h2>Analytics <span className="gradient-name">Dashboard</span></h2>
            <p>Real-time emotion tracking, fusion data, and session summary.</p>
          </div>
          <div className="glass-panel" style={{ padding: 0, flex: 1, overflow: 'hidden' }}>
            <AnalyticsDashboard
              currentEmotion={currentEmotion}
              faceConfidence={faceConfidence}
              voiceEmotion={voiceEmotion}
              voiceConfidence={voiceConfidence}
            />
          </div>
        </div>
      )}

      {/* ═══════════ MEMORIES TAB ═══════════ */}
      {activeTab === 'memories' && (
        <div className="tab-content-full">
          <div className="tab-header">
            <h2>Memory <span className="gradient-name">Timeline</span></h2>
            <p>All stored memories — searchable and filterable.</p>
          </div>
          <div className="glass-panel" style={{ padding: 0, flex: 1, overflow: 'hidden' }}>
            <MemoryTimeline onHighlightMemory={(id) => console.log('Highlight in 3D:', id)} />
          </div>
        </div>
      )}

      {/* ═══════════ PROFILE TAB ═══════════ */}
      {activeTab === 'profile' && (
        <div className="tab-content-full">
          <div className="tab-header">
            <h2>Your <span className="gradient-name">Profile</span></h2>
          </div>
          <div className="glass-panel" style={{ padding: 0, flex: 1, overflow: 'auto' }}>
            <ProfileTabContent />
          </div>
        </div>
      )}
    </div>
  );
};

const ProfileTabContent: React.FC = () => {
  const Profile = React.lazy(() => import('./Profile'));
  return (
    <React.Suspense fallback={<div style={{ padding: '40px', textAlign: 'center', color: 'rgba(255,255,255,0.4)' }}>Loading profile...</div>}>
      <Profile />
    </React.Suspense>
  );
};

export default PremiumDashboard;
