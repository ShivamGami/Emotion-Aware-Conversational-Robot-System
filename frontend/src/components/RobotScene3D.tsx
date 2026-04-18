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
 *   GET /api/ros/current_emotion
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
        background: `#02040a`,
        transition: 'background 0.8s ease',
        perspective: '1000px',
      }}
    >
      {/* 3D Grid Floor */}
      <div style={{
        position: 'absolute',
        bottom: '-20%', left: '-50%', right: '-50%', height: '80%',
        backgroundSize: '40px 40px',
        backgroundImage: 'linear-gradient(to right, rgba(0, 212, 255, 0.1) 1px, transparent 1px), linear-gradient(to bottom, rgba(0, 212, 255, 0.1) 1px, transparent 1px)',
        transform: 'rotateX(75deg)',
        transformOrigin: 'top',
        maskImage: 'linear-gradient(to bottom, transparent, black 10%, black 80%, transparent)',
        WebkitMaskImage: 'linear-gradient(to bottom, transparent, black 10%, black 80%, transparent)',
      }} />

      {/* Central Base Rings (Simulating 3D floor rings) */}
      <div style={{
        position: 'absolute',
        bottom: '25%', left: '50%',
        transform: 'translate(-50%, 50%) rotateX(75deg)',
        width: '400px', height: '400px',
        borderRadius: '50%',
        border: '10px solid rgba(0, 212, 255, 0.6)',
        boxShadow: '0 0 40px rgba(0, 212, 255, 0.4), inset 0 0 20px rgba(0, 212, 255, 0.2)',
      }} />
      <div style={{
        position: 'absolute',
        bottom: '25%', left: '50%',
        transform: 'translate(-50%, 50%) rotateX(75deg)',
        width: '200px', height: '200px',
        borderRadius: '50%',
        border: '4px solid rgba(0, 212, 255, 0.4)',
      }} />
      <div style={{
        position: 'absolute',
        bottom: '25%', left: '50%',
        transform: 'translate(-50%, 50%) rotateX(75deg)',
        width: '80px', height: '80px',
        borderRadius: '50%',
        border: '6px solid rgba(0, 212, 255, 0.8)',
        boxShadow: '0 0 20px rgba(0, 212, 255, 0.6)',
      }} />

      {/* Vertical Avatar Building Blocks (The "Blob" Robot) */}
      <div style={{
        position: 'absolute',
        bottom: '15%', left: '50%',
        transform: 'translateX(-50%)',
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        gap: '10px', zIndex: 5,
        filter: 'drop-shadow(0 0 10px rgba(0, 212, 255, 0.8))',
      }}>
         {/* Head Area */}
         <div style={{ width: '6px', height: '20px', background: 'var(--accent)', borderRadius: '4px' }} />
         <div style={{ width: '40px', height: '14px', background: 'var(--accent)', borderRadius: '8px', marginBottom: '8px' }} />

         {/* Spine / Body blobs */}
         <div style={{ width: '24px', height: '30px', background: 'var(--accent)', borderRadius: '50%' }} />
         <div style={{ width: '20px', height: '20px', background: 'var(--accent)', borderRadius: '50%' }} />
         <div style={{ width: '16px', height: '16px', background: 'var(--accent)', borderRadius: '50%' }} />
         <div style={{ width: '20px', height: '20px', background: 'var(--accent)', borderRadius: '50%' }} />
         <div style={{ width: '24px', height: '10px', background: 'var(--accent)', borderRadius: '4px' }} />
      </div>

      {/* Floating Shapes */}
      {/* Heavy Hexagon */}
      <div style={{
        position: 'absolute', left: '30%', top: '40%',
        width: '60px', height: '65px',
        background: 'rgba(0, 150, 200, 0.8)',
        clipPath: 'polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%)',
        boxShadow: '0 0 20px rgba(0,212,255,0.4)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        animation: 'float 6s ease-in-out infinite',
      }}>
        <div style={{ width: '12px', height: '12px', background: 'white', borderRadius: '50%', boxShadow: '0 0 10px white' }} />
      </div>

      {/* Particles around */}
      <div style={{ position: 'absolute', left: '46%', top: '50%', width:'12px', height:'12px', background: '#ffcc00', borderRadius:'50%', boxShadow:'0 0 10px #ffcc00', animation: 'float 4s infinite alternate' }} />
      <div style={{ position: 'absolute', left: '16%', top: '56%', width:'24px', height:'24px', background: '#e63946', borderRadius:'50%', boxShadow:'0 0 15px #e63946', animation: 'float 5s infinite alternate' }} />
      <div style={{ position: 'absolute', right: '24%', top: '42%', width:'16px', height:'16px', background: '#9d4edd', borderRadius:'50%', boxShadow:'0 0 15px #9d4edd', animation: 'float 7s infinite alternate' }} />
      <div style={{ position: 'absolute', right: '15%', top: '25%', width:'8px', height:'8px', background: 'rgba(0,212,255,0.6)', borderRadius:'50%', animation: 'float 3s infinite alternate' }} />
      <div style={{ position: 'absolute', left: '32%', top: '22%', width:'6px', height:'6px', background: 'rgba(0,212,255,0.8)', borderRadius:'50%', animation: 'float 5s infinite alternate' }} />

      {/* Tiny floating stars/dots */}
      {[...Array(15)].map((_, i) => (
         <div key={i} style={{ 
            position: 'absolute', 
            left: `${Math.random() * 90}%`, 
            top: `${Math.random() * 80}%`, 
            width: `${Math.random() * 3 + 1}px`, 
            height: `${Math.random() * 3 + 1}px`, 
            background: 'rgba(0,212,255,0.5)', 
            borderRadius: '50%',
            animation: `pulse ${Math.random() * 2 + 1}s infinite alternate`
         }} />
      ))}


      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.6; transform: scale(0.9); }
        }
        @keyframes float {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-15px); }
        }
      `}</style>
    </div>
  );
};

export default RobotScene3D;
