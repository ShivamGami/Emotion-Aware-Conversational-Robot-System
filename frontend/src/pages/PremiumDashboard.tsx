import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { useSpeech } from '../hooks/useSpeech';
import EmotionCamera from '../components/EmotionCamera';
import SubtitleOverlay from '../components/SubtitleOverlay';
import RobotScene3D from '../components/RobotScene3D';
import MemoryTimeline from '../components/MemoryTimeline';
import AnalyticsDashboard from '../components/AnalyticsDashboard';
import '../styles/PremiumDashboard.css';
import { LogOut, User, BarChart2, Brain, Home, Mic, MicOff } from 'lucide-react';

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
  
  const [subtitle, setSubtitle] = useState({ text: '', isVisible: false });

  // ── Orchestration: The Brain ──
  const processConversation = useCallback(async (userText: string) => {
    try {
      // 1. Send text + current emotion to LLM
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}` // Assuming token storage
        },
        body: JSON.stringify({
          text: userText,
          emotion: currentEmotion
        }),
      });

      if (!response.ok) throw new Error('Chat API failed');
      const data = await response.json();

      // 2. Display Subtitles
      setSubtitle({ text: data.response, isVisible: true });

      // 3. Notify Bridge - Speech START
      await fetch('http://localhost:8000/api/bridge/speech_state', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_speaking: true, text: data.response }),
      });

      // 4. Trigger TTS
      speak(data.response, data.speak_with_emotion, data.voice_settings, async () => {
        // Callback when speech ENDS
        setSubtitle(s => ({ ...s, isVisible: false }));
        
        // Notify Bridge - Speech END
        await fetch('http://localhost:8000/api/bridge/speech_state', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ is_speaking: false }),
        });
      });

    } catch (error) {
      console.error('Brain Processing Error:', error);
    }
  }, [currentEmotion, speak]);

  // ── Continuous Monitoring ──
  React.useEffect(() => {
    // Start continuous voice monitoring
    startVoiceEmotionMonitoring((emotion, confidence) => {
      setVoiceEmotion(emotion);
      setVoiceConfidence(confidence);
    });
  }, [startVoiceEmotionMonitoring]);

  const handleStartInteraction = () => {
    startListening((text) => {
      processConversation(text);
    });
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
            {/* Robot 3D - Emotion flows in */}
            <RobotScene3D emotion={currentEmotion} />
          </div>

          <SubtitleOverlay 
            text={subtitle.text}
            speaker="EmoBot"
            isVisible={subtitle.isVisible}
            emotion={currentEmotion}
          />

          {/* Top Left: Webcam */}
          <div className="floating-panel top-left animate-slide-in-left">
            <div className="glass-panel webcam-mini">
              <EmotionCamera onEmotionChange={handleEmotionChange} />
            </div>
          </div>

          {/* Master Control: The Mic Button */}
          <div className="floating-panel bottom-center">
            <button 
              className={`mic-trigger-btn ${isListening ? 'listening' : ''} ${isSpeaking ? 'speaking' : ''}`}
              onClick={handleStartInteraction}
              disabled={isSpeaking}
            >
              {isListening ? <MicOff size={32} /> : <Mic size={32} />}
              <span className="btn-label">
                {isListening ? 'Listening...' : isSpeaking ? 'Robot Speaking' : 'Click to Speak'}
              </span>
            </button>
          </div>

          <div className="studio-greeting">
            <h2 className="studio-title">
              Hello, <span className="gradient-name">{user?.username}</span>
            </h2>
            <p className="studio-sub">Emotion-Aware OS v2.0</p>
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
