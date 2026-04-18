import React, { useState, useEffect } from 'react';
import EmotionCamera from '../components/EmotionCamera';
import '../index.css';

const Studio: React.FC = () => {
  // Mock conversation state mapped to the subtitle view
  const [subtitle, setSubtitle] = useState({ speaker: 'EmoBot', text: 'Initializing Unreal Engine streaming layer...' });

  useEffect(() => {
    // Demonstration loop to show off Netflix subtitle interaction dynamically
    const dialogue = [
      { speaker: 'EmoBot', text: 'System diagnostics complete. ROS2 bridge online.' },
      { speaker: 'You', text: 'How are you feeling today?' },
      { speaker: 'EmoBot', text: 'I am functioning nominally within the simulation.' },
      { speaker: 'You', text: 'Awesome. This UI looks incredible.' },
      { speaker: 'EmoBot', text: 'Thank you. Integrating physical movements now.' }
    ];
    let i = 0;
    const timer = setInterval(() => {
      setSubtitle(dialogue[i % dialogue.length]);
      i++;
    }, 4500);
    return () => clearInterval(timer);
  }, []);

  return (
    <div style={{ position: 'relative', width: '100vw', height: '100vh', backgroundColor: '#000' }}>
      
      {/* 1. LAYER ONE: Unreal Engine Video Canvas (Backdrop) */}
      {/* For demonstration before Member 4's Unreal Server is live, we use an immersive sci-fi placeholder video */}
      <video 
        autoPlay 
        loop 
        muted 
        playsInline
        style={{ 
          position: 'absolute', 
          width: '100%', 
          height: '100%', 
          objectFit: 'cover',
          zIndex: 0,
          opacity: 0.85
        }}
        src="https://cdn.pixabay.com/video/2021/08/04/83896-585145880_large.mp4"
      />

      {/* 2. LAYER TWO: Vision Pro Floating UI */}
      <div style={{ position: 'absolute', inset: 0, zIndex: 1, pointerEvents: 'none', padding: '32px' }}>
        
        {/* Top Right: ROS2 Status Panel */}
        <div 
          className="glass-panel" 
          style={{ 
            position: 'absolute', 
            top: '32px', 
            right: '32px', 
            width: '280px', 
            padding: '20px',
            pointerEvents: 'auto'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
             <h3 style={{ margin: 0, fontSize: '0.85rem', letterSpacing: '2px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>ROS Status</h3>
          </div>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '0.9rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--success-green)', boxShadow: '0 0 10px var(--success-green)' }} />
              <span>Connected</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--success-green)', boxShadow: '0 0 10px var(--success-green)' }} />
              <span>Unreal Engine Running</span>
            </div>
            
            <div style={{ borderTop: '1px solid var(--glass-border)', paddingTop: '12px', marginTop: '4px', display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)' }}>
              <span>Latency</span>
              <span style={{ color: 'white' }}>32ms</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)' }}>
              <span>Last Command</span>
              <span style={{ color: 'var(--ros-cyan)' }}>idle_breath</span>
            </div>
          </div>
        </div>

        {/* Top Left: Webcam & Emotion Processing */}
        <div 
          className="glass-panel" 
          style={{ 
            position: 'absolute', 
            top: '32px', 
            left: '32px', 
            width: '240px',
            padding: '12px',
            pointerEvents: 'auto'
          }}
        >
          {/* EmotionCamera fits constrained inside this small left window now */}
          <div style={{ width: '100%', height: '140px', borderRadius: '12px', overflow: 'hidden' }}>
             <EmotionCamera />
          </div>
        </div>

        {/* Bottom Center: Netflix-Style Subtitle Conversational UI */}
        <div 
          className="subtitle-container"
          style={{ 
            position: 'absolute', 
            bottom: '0', 
            left: '0', 
            right: '0', 
            height: '280px',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'flex-end',
            alignItems: 'center',
            paddingBottom: '80px',
            pointerEvents: 'auto'
          }}
        >
          <div 
            style={{ 
              maxWidth: '800px', 
              textAlign: 'center',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
              animation: 'fadeInOut 4.5s infinite' 
            }}
          >
            <span style={{ 
              fontSize: '1rem', 
              fontWeight: 500, 
              color: subtitle.speaker === 'You' ? 'white' : 'var(--ros-cyan)',
              letterSpacing: '1px'
            }}>
              {subtitle.speaker.toUpperCase()}
            </span>
            <p style={{ 
              margin: 0, 
              fontSize: '2.2rem', 
              fontWeight: 300, 
              lineHeight: 1.4 
            }}>
              "{subtitle.text}"
            </p>
          </div>

          {/* Hidden Mic input Trigger - Keeps the UI clean */}
          <button style={{ 
            marginTop: '32px', 
            background: 'var(--glass-highlight)', 
            border: '1px solid var(--glass-border)', 
            borderRadius: '30px', 
            padding: '12px 32px',
            color: 'white',
            cursor: 'pointer',
            backdropFilter: 'blur(12px)',
            transition: 'all 0.3s ease'
          }}>
            Hold Spacebar to Speak
          </button>
        </div>

      </div>

      <style>{`
        @keyframes fadeInOut {
          0% { opacity: 0; transform: translateY(10px); }
          10% { opacity: 1; transform: translateY(0); }
          90% { opacity: 1; transform: translateY(0); }
          100% { opacity: 0; transform: translateY(-10px); }
        }
      `}</style>
    </div>
  );
};

export default Studio;
