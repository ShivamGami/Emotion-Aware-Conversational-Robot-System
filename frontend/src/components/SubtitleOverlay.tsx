import React from 'react';

interface SubtitleOverlayProps {
  text: string;
  speaker: 'You' | 'EmoBot' | string;
  isVisible: boolean;
  emotion?: string;
  isThinking?: boolean;
}

const SubtitleOverlay: React.FC<SubtitleOverlayProps> = ({ 
  text, speaker, isVisible, emotion = 'neutral', isThinking = false 
}) => {
  if (!isVisible) return null;

  const isUser = speaker === 'You';
  
  const getAccentColor = () => {
    if (isUser) return '#ffffff';
    switch (emotion.toLowerCase()) {
      case 'happy': return '#ffd700';
      case 'sad': return '#4169e1';
      case 'angry': return '#ff4444';
      case 'fearful': return '#9400d3';
      case 'surprised': return '#ff8c00';
      case 'surprise': return '#ff8c00';
      default: return '#00d4ff';
    }
  };

  const color = getAccentColor();

  return (
    <div className="subtitle-overlay animate-fade-in" style={{
      position: 'absolute',
      bottom: '100px',
      left: '50%',
      transform: 'translateX(-50%)',
      width: '80%',
      maxWidth: '800px',
      textAlign: 'center',
      zIndex: 1000,
      pointerEvents: 'none',
    }}>
      <div style={{
        backgroundColor: 'rgba(0, 0, 0, 0.65)',
        backdropFilter: 'blur(12px)',
        padding: '16px 32px',
        borderRadius: '14px',
        border: `1px solid ${color}30`,
        boxShadow: `0 10px 40px rgba(0,0,0,0.5), 0 0 20px ${color}10`,
        animation: 'subtitleSlideUp 0.3s ease-out',
      }}>
        {/* Speaker Label */}
        <div style={{
          fontSize: '0.75rem',
          textTransform: 'uppercase',
          letterSpacing: '3px',
          color: color,
          marginBottom: '8px',
          fontWeight: 700,
          opacity: 0.9,
        }}>
          {isUser ? '🎤 YOU' : '🤖 EMOBOT'}
        </div>

        {/* Text or Thinking Animation */}
        {isThinking ? (
          <div style={{
            display: 'flex',
            justifyContent: 'center',
            gap: '6px',
            padding: '8px 0',
          }}>
            {[0, 1, 2].map(i => (
              <span key={i} style={{
                width: '8px', height: '8px',
                borderRadius: '50%',
                backgroundColor: color,
                opacity: 0.6,
                animation: `thinkingDot 1.2s ease-in-out ${i * 0.2}s infinite`,
              }} />
            ))}
          </div>
        ) : (
          <p style={{
            margin: 0,
            fontSize: isUser ? '1.4rem' : '1.7rem',
            lineHeight: 1.5,
            color: 'white',
            fontWeight: isUser ? 400 : 300,
            fontStyle: isUser ? 'italic' : 'normal',
            textShadow: '0 2px 4px rgba(0,0,0,0.5)',
          }}>
            "{text}"
          </p>
        )}
      </div>

      <style>{`
        @keyframes subtitleSlideUp {
          from { opacity: 0; transform: translateX(-50%) translateY(15px); }
          to { opacity: 1; transform: translateX(-50%) translateY(0); }
        }
        @keyframes thinkingDot {
          0%, 80%, 100% { transform: scale(0.6); opacity: 0.3; }
          40% { transform: scale(1.0); opacity: 1; }
        }
      `}</style>
    </div>
  );
};

export default SubtitleOverlay;
