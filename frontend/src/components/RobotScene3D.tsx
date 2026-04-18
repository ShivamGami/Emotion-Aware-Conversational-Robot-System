import React, { useEffect, useState, useRef } from 'react';

/**
 * RobotScene3D — Member 4's Integration Slot
 * ─────────────────────────────────────────────────────
 * This component receives the current detected `emotion` as a prop.
 * Member 4 replaces the contents of this component with their
 * React Three Fiber Canvas (3D robot, environment, particles etc.)
 *
 * HOW TO INTEGRATE (Member 4):
 *   1. Import your MainScene / Canvas component here
 *   2. Replace the placeholder <div> with your <Canvas> component
 *   3. Pass `emotion` prop into your scene for animation switching
 *   4. The container is already styled — do NOT change the outer wrapper
 *
 * API endpoint available:
 *   GET http://localhost:8000/api/ros/current_emotion
 *   → { emotion: "happy", behavior: { animation: "dance", speed: 1.2, color: "#ffd700" } }
 */

const EMOTION_COLORS: Record<string, string> = {
  happy: '#ffd700', sad: '#4169e1', angry: '#ff4444',
  fearful: '#9400d3', surprised: '#ff8c00', disgust: '#556b2f',
  calm: '#00ced1', neutral: '#00d4ff',
};

const EMOTION_ANIMATIONS: Record<string, string> = {
  happy: '🕺 Dancing', sad: '😞 Head Down', angry: '😤 Stomping',
  fearful: '😨 Cowering', surprised: '😲 Jumping Back',
  disgust: '🤢 Turning Away', calm: '🧘 Idle Breath', neutral: '🤖 Idle Breath',
};

const EMOTION_BG: Record<string, string> = {
  happy: 'radial-gradient(ellipse at center, rgba(255,215,0,0.15) 0%, transparent 70%)',
  sad: 'radial-gradient(ellipse at center, rgba(65,105,225,0.15) 0%, transparent 70%)',
  angry: 'radial-gradient(ellipse at center, rgba(255,68,68,0.15) 0%, transparent 70%)',
  fearful: 'radial-gradient(ellipse at center, rgba(148,0,211,0.15) 0%, transparent 70%)',
  surprised: 'radial-gradient(ellipse at center, rgba(255,140,0,0.15) 0%, transparent 70%)',
  calm: 'radial-gradient(ellipse at center, rgba(0,206,209,0.15) 0%, transparent 70%)',
  neutral: 'radial-gradient(ellipse at center, rgba(0,212,255,0.12) 0%, transparent 70%)',
  disgust: 'radial-gradient(ellipse at center, rgba(85,107,47,0.15) 0%, transparent 70%)',
};

interface RobotScene3DProps {
  emotion: string;
}

const RobotScene3D: React.FC<RobotScene3DProps> = ({ emotion }) => {
  const color = EMOTION_COLORS[emotion] || '#00d4ff';
  const animation = EMOTION_ANIMATIONS[emotion] || '🤖 Idle';
  const bg = EMOTION_BG[emotion] || EMOTION_BG['neutral'];

  // Orbiting particle simulation (CSS animation, no Three.js needed for placeholder)
  const [orbitAngle, setOrbitAngle] = useState(0);
  const rafRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    const animate = () => {
      setOrbitAngle((a) => (a + 0.5) % 360);
      rafRef.current = requestAnimationFrame(animate);
    };
    rafRef.current = requestAnimationFrame(animate);
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); };
  }, []);

  const orbitX = 50 + 36 * Math.cos((orbitAngle * Math.PI) / 180);
  const orbitY = 50 + 18 * Math.sin((orbitAngle * Math.PI) / 180);
  const orbit2X = 50 + 36 * Math.cos(((orbitAngle + 120) * Math.PI) / 180);
  const orbit2Y = 50 + 18 * Math.sin(((orbitAngle + 120) * Math.PI) / 180);
  const orbit3X = 50 + 36 * Math.cos(((orbitAngle + 240) * Math.PI) / 180);
  const orbit3Y = 50 + 18 * Math.sin(((orbitAngle + 240) * Math.PI) / 180);

  return (
    <div
      id="robot-scene-3d-container"
      style={{
        width: '100%', height: '100%', minHeight: '380px',
        position: 'relative', overflow: 'hidden', borderRadius: '16px',
        background: `#060a14`,
        transition: 'all 0.8s ease',
      }}
    >
      {/* Dynamic emotion background glow */}
      <div style={{
        position: 'absolute', inset: 0,
        background: bg,
        transition: 'background 1s ease',
        pointerEvents: 'none',
      }} />

      {/* ─────────────────────────────────────────────
          MEMBER 4: Replace everything inside this div
          with your React Three Fiber <Canvas> component.
          Keep the outer wrapper intact.
          ───────────────────────────────────────────── */}
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        gap: '16px',
      }}>

        {/* Animated SVG Robot placeholder */}
        <svg width="120" height="160" viewBox="0 0 120 160" fill="none">
          {/* Head */}
          <rect x="30" y="20" width="60" height="50" rx="12"
            fill={`${color}22`} stroke={color} strokeWidth="2"
            style={{ filter: `drop-shadow(0 0 8px ${color})` }} />
          {/* Eyes */}
          <circle cx="45" cy="40" r="8" fill={color} opacity="0.9"
            style={{ animation: 'pulse 1.5s ease-in-out infinite' }} />
          <circle cx="75" cy="40" r="8" fill={color} opacity="0.9"
            style={{ animation: 'pulse 1.5s ease-in-out infinite 0.3s' }} />
          {/* Mouth — changes by emotion */}
          {emotion === 'happy' && (
            <path d="M 42 55 Q 60 68 78 55" stroke={color} strokeWidth="3" fill="none" strokeLinecap="round" />
          )}
          {emotion === 'sad' && (
            <path d="M 42 62 Q 60 52 78 62" stroke={color} strokeWidth="3" fill="none" strokeLinecap="round" />
          )}
          {(emotion === 'neutral' || emotion === 'calm') && (
            <line x1="45" y1="58" x2="75" y2="58" stroke={color} strokeWidth="3" strokeLinecap="round" />
          )}
          {emotion === 'angry' && (
            <path d="M 42 62 Q 60 52 78 62" stroke="#ff4444" strokeWidth="3" fill="none" strokeLinecap="round" />
          )}
          {emotion === 'surprised' && (
            <ellipse cx="60" cy="58" rx="8" ry="6" stroke={color} strokeWidth="2" fill="none" />
          )}
          {/* Antenna */}
          <line x1="60" y1="20" x2="60" y2="8" stroke={color} strokeWidth="2" />
          <circle cx="60" cy="6" r="4" fill={color}
            style={{ animation: 'pulse 1s ease-in-out infinite' }} />
          {/* Body */}
          <rect x="20" y="75" width="80" height="55" rx="10"
            fill={`${color}15`} stroke={color} strokeWidth="1.5" />
          {/* Chest panel */}
          <rect x="35" y="85" width="50" height="30" rx="6"
            fill={`${color}30`} stroke={`${color}80`} strokeWidth="1" />
          <circle cx="60" cy="100" r="8" fill={`${color}60`} stroke={color} strokeWidth="1.5"
            style={{ filter: `drop-shadow(0 0 6px ${color})` }} />
          {/* Arms */}
          <rect x="2" y="78" width="15" height="40" rx="7"
            fill={`${color}20`} stroke={color} strokeWidth="1.5" />
          <rect x="103" y="78" width="15" height="40" rx="7"
            fill={`${color}20`} stroke={color} strokeWidth="1.5" />
          {/* Legs */}
          <rect x="30" y="132" width="22" height="24" rx="8"
            fill={`${color}20`} stroke={color} strokeWidth="1.5" />
          <rect x="68" y="132" width="22" height="24" rx="8"
            fill={`${color}20`} stroke={color} strokeWidth="1.5" />
        </svg>

        {/* Animation label */}
        <div style={{
          color, fontSize: '0.9rem', fontWeight: 600,
          background: `${color}15`, padding: '6px 16px',
          borderRadius: '20px', border: `1px solid ${color}40`,
          letterSpacing: '0.5px',
        }}>
          {animation}
        </div>

        {/* M4 integration message */}
        <div style={{
          color: 'rgba(255,255,255,0.3)', fontSize: '0.7rem',
          textAlign: 'center', maxWidth: '200px',
          lineHeight: 1.5,
        }}>
          M4 drops React Three Fiber Canvas here
        </div>
      </div>

      {/* Orbiting memory orbs */}
      {[
        { x: orbitX, y: orbitY, label: '☕ Coffee' },
        { x: orbit2X, y: orbit2Y, label: '💼 Work' },
        { x: orbit3X, y: orbit3Y, label: '🌙 Calm' },
      ].map((orb, i) => (
        <div key={i} style={{
          position: 'absolute',
          left: `${orb.x}%`, top: `${orb.y}%`,
          transform: 'translate(-50%, -50%)',
          background: `${color}25`, border: `1px solid ${color}60`,
          borderRadius: '50%', width: '48px', height: '48px',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '0.6rem', color: 'white', textAlign: 'center',
          backdropFilter: 'blur(4px)',
          boxShadow: `0 0 12px ${color}40`,
          cursor: 'pointer',
          transition: 'box-shadow 0.3s ease',
          lineHeight: 1.2,
        }}>
          {orb.label}
        </div>
      ))}

      {/* Bottom emotion info bar */}
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0,
        background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(10px)',
        padding: '10px 20px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        borderTop: `1px solid ${color}30`,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{
            width: '8px', height: '8px', borderRadius: '50%',
            background: color, boxShadow: `0 0 8px ${color}`,
          }} />
          <span style={{ color, fontSize: '0.8rem', fontWeight: 600 }}>
            {emotion.toUpperCase()}
          </span>
        </div>
        <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.75rem' }}>
          3D World Container — M4
        </span>
        <div style={{ display: 'flex', gap: '6px' }}>
          {['robot', 'env', 'ctx'].map((t) => (
            <div key={t} style={{
              padding: '2px 8px', borderRadius: '4px',
              background: 'rgba(255,255,255,0.05)',
              color: 'rgba(255,255,255,0.3)', fontSize: '0.65rem',
            }}>{t}</div>
          ))}
        </div>
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.6; transform: scale(0.9); }
        }
      `}</style>
    </div>
  );
};

export default RobotScene3D;
