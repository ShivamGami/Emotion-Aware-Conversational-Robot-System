import React from 'react';

interface SubtitleOverlayProps {
  text: string;
  speaker: string;
  isVisible: boolean;
  emotion?: string;
}

const SubtitleOverlay: React.FC<SubtitleOverlayProps> = ({ text, speaker, isVisible, emotion = 'neutral' }) => {
  if (!isVisible || !text) return null;

  const getEmotionColor = () => {
    switch (emotion.toLowerCase()) {
      case 'happy': return '#ffd700'; // Gold
      case 'sad': return '#4169e1'; // Royal Blue
      case 'angry': return '#ff4444'; // Red
      case 'fearful': return '#9400d3'; // Purple
      default: return '#00d4ff'; // Cyan
    }
  };

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
      pointerEvents: 'none'
    }}>
      <div style={{
        backgroundColor: 'rgba(0, 0, 0, 0.6)',
        backdropFilter: 'blur(10px)',
        padding: '16px 32px',
        borderRadius: '12px',
        border: `1px solid ${getEmotionColor()}40`,
        boxShadow: `0 10px 30px rgba(0,0,0,0.5), 0 0 20px ${getEmotionColor()}10`
      }}>
        <div style={{
          fontSize: '0.8rem',
          textTransform: 'uppercase',
          letterSpacing: '2px',
          color: getEmotionColor(),
          marginBottom: '8px',
          fontWeight: 600
        }}>
          {speaker}
        </div>
        <p style={{
          margin: 0,
          fontSize: '1.8rem',
          lineHeight: 1.4,
          color: 'white',
          fontWeight: 300,
          textShadow: '0 2px 4px rgba(0,0,0,0.5)'
        }}>
          "{text}"
        </p>
      </div>
    </div>
  );
};

export default SubtitleOverlay;
