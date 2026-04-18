import React, { useEffect, useState, useRef } from 'react';
import { useAuthStore } from '../store/authStore';

const EMOTIONS = ['happy', 'neutral', 'sad', 'angry', 'fearful', 'surprised', 'calm'];
const EMOTION_ICONS: Record<string, string> = {
  happy: '😊', sad: '😢', angry: '😠', fearful: '😨',
  surprised: '😲', disgust: '🤢', calm: '😌', neutral: '🤖',
};
const EMOTION_COLORS: Record<string, string> = {
  happy: '#ffd700', sad: '#4169e1', angry: '#ff4444',
  fearful: '#9400d3', surprised: '#ff8c00', calm: '#00ced1', neutral: '#00d4ff',
  disgust: '#778826',
};

interface EmotionEntry { time: string; emotion: string; value: number; }
interface AnalyticsDashboardProps {
  currentEmotion: string;
  faceConfidence: number;
  voiceEmotion: string;
  voiceConfidence: number;
}

const AnalyticsDashboard: React.FC<AnalyticsDashboardProps> = ({
  currentEmotion, faceConfidence, voiceEmotion, voiceConfidence,
}) => {
  const [history, setHistory] = useState<EmotionEntry[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [fuseResult, setFuseResult] = useState<any>(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const token = useAuthStore((s) => s.token);
  const lastFuseRef = useRef<string>('');

  // ── Emotion history: add entry every 3 seconds ─────────────────────────────
  useEffect(() => {
    const interval = setInterval(() => {
      const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      setHistory(prev => [
        ...prev.slice(-19),
        {
          time: now,
          emotion: currentEmotion,
          value: Math.max(10, Math.round((faceConfidence || 0.5) * 100)),
        }
      ]);
    }, 3000);
    return () => clearInterval(interval);
  }, [currentEmotion, faceConfidence]);

  // ── Multimodal Fusion — fixed URL: /api/fuse (not /api/fuse_emotions) ──────
  // Also fixed request body keys to match FusionRequest schema
  useEffect(() => {
    if (!currentEmotion || !voiceEmotion) return;

    // Debounce: don't call if emotion combo hasn't changed
    const fuseKey = `${currentEmotion}:${voiceEmotion}`;
    if (fuseKey === lastFuseRef.current) return;
    lastFuseRef.current = fuseKey;

    fetch('http://localhost:8000/api/fuse', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        face_emotion: currentEmotion,
        face_confidence: faceConfidence || 0.75,
        voice_emotion: voiceEmotion,
        voice_confidence: voiceConfidence || 0.65,
      }),
    })
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setFuseResult(data); })
      .catch(() => {});
  }, [currentEmotion, voiceEmotion, faceConfidence, voiceConfidence]);

  // ── Fetch user stats ────────────────────────────────────────────────────────
  useEffect(() => {
    if (!token) return;
    setStatsLoading(true);
    fetch('http://localhost:8000/api/user/stats', {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    })
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data) setStats(data);
      })
      .catch((err) => console.error('Analytics Error:', err))
      .finally(() => setStatsLoading(false));
  }, [token]);

  // ── Radar chart data ────────────────────────────────────────────────────────
  const radarValues = EMOTIONS.reduce<Record<string, number>>((acc, e) => {
    // Use real backend data if available, otherwise use current reading
    acc[e] = stats?.emotion_breakdown?.[e] || (e === currentEmotion ? 1 : 0);
    return acc;
  }, {});
  const maxVal = Math.max(...Object.values(radarValues), 1);

  const centerX = 90, centerY = 90, radius = 70;
  const radarPoints = EMOTIONS.map((_, i) => {
    const angle = (i / EMOTIONS.length) * 2 * Math.PI - Math.PI / 2;
    return { x: centerX + radius * Math.cos(angle), y: centerY + radius * Math.sin(angle) };
  });
  const dataPoints = EMOTIONS.map((e, i) => {
    const angle = (i / EMOTIONS.length) * 2 * Math.PI - Math.PI / 2;
    const r = (radarValues[e] / maxVal) * radius;
    return `${centerX + r * Math.cos(angle)},${centerY + r * Math.sin(angle)}`;
  }).join(' ');

  const faceColor = EMOTION_COLORS[currentEmotion] || '#00d4ff';
  const voiceColor = EMOTION_COLORS[voiceEmotion] || '#ff69b4';
  const fusedEmotion = fuseResult?.fused_emotion || currentEmotion;
  const fusedColor = EMOTION_COLORS[fusedEmotion] || '#00d4ff';

  return (
    <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px', height: '100%', overflowY: 'auto' }}>

      {/* ── Row 1: Fusion Panel ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
        {[
          { label: 'Face', emotion: currentEmotion, confidence: Math.round((faceConfidence || 0.5) * 100), color: faceColor, icon: EMOTION_ICONS[currentEmotion] || '🤖' },
          { label: 'Voice', emotion: voiceEmotion || 'neutral', confidence: Math.round((voiceConfidence || 0.5) * 100), color: voiceColor, icon: EMOTION_ICONS[voiceEmotion] || '🎤' },
          {
            label: 'Fused', emotion: fusedEmotion, color: fusedColor, icon: '⚡',
            confidence: fuseResult
              ? Math.round(((faceConfidence || 0.5) + (voiceConfidence || 0.5)) / 2 * 100)
              : Math.round((faceConfidence || 0.5) * 100),
          },
        ].map(card => (
          <div key={card.label} style={{
            background: `${card.color}10`, border: `1px solid ${card.color}40`,
            borderRadius: '14px', padding: '14px', textAlign: 'center',
            transition: 'all 0.5s ease',
          }}>
            <div style={{ fontSize: '1.8rem', marginBottom: '4px' }}>{card.icon}</div>
            <div style={{ color: card.color, fontWeight: 700, fontSize: '1rem' }}>{card.emotion.toUpperCase()}</div>
            <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.75rem', marginTop: '2px' }}>{card.label}</div>
            <div style={{ marginTop: '8px', background: 'rgba(255,255,255,0.1)', borderRadius: '4px', height: '5px' }}>
              <div style={{ width: `${card.confidence}%`, height: '5px', background: card.color, borderRadius: '4px', transition: 'width 0.5s ease' }} />
            </div>
            <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.7rem', marginTop: '4px' }}>{card.confidence}%</div>
          </div>
        ))}
      </div>

      {/* ── Row 2: Radar + Timeline ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr', gap: '12px' }}>

        {/* Radar Chart */}
        <div style={{ background: 'rgba(255,255,255,0.04)', borderRadius: '14px', padding: '12px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', marginBottom: '8px', letterSpacing: '1px' }}>EMOTION RADAR</div>
          <svg width="180" height="180" viewBox="0 0 180 180">
            {/* Grid rings */}
            {[0.25, 0.5, 0.75, 1].map((scale, i) => (
              <polygon key={i} points={radarPoints.map((_, j) => {
                const angle = (j / EMOTIONS.length) * 2 * Math.PI - Math.PI / 2;
                return `${centerX + radius * scale * Math.cos(angle)},${centerY + radius * scale * Math.sin(angle)}`;
              }).join(' ')} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="1" />
            ))}
            {/* Axes */}
            {radarPoints.map((p, i) => (
              <line key={i} x1={centerX} y1={centerY} x2={p.x} y2={p.y} stroke="rgba(255,255,255,0.08)" strokeWidth="1" />
            ))}
            {/* Data polygon — animates as emotions change */}
            <polygon
              points={dataPoints}
              fill={`${fusedColor}30`}
              stroke={fusedColor}
              strokeWidth="2"
              style={{ transition: 'all 0.8s ease' }}
            />
            {/* Dot on current emotion axis */}
            {EMOTIONS.map((e, i) => {
              const angle = (i / EMOTIONS.length) * 2 * Math.PI - Math.PI / 2;
              const r = (radarValues[e] / maxVal) * radius;
              return (
                <circle
                  key={e}
                  cx={centerX + r * Math.cos(angle)}
                  cy={centerY + r * Math.sin(angle)}
                  r={e === currentEmotion || e === fusedEmotion ? 4 : 2.5}
                  fill={e === currentEmotion ? faceColor : e === fusedEmotion ? fusedColor : 'rgba(255,255,255,0.3)'}
                  style={{ transition: 'all 0.4s ease' }}
                />
              );
            })}
            {/* Labels */}
            {EMOTIONS.map((e, i) => {
              const angle = (i / EMOTIONS.length) * 2 * Math.PI - Math.PI / 2;
              const lx = centerX + (radius + 14) * Math.cos(angle);
              const ly = centerY + (radius + 14) * Math.sin(angle);
              return (
                <text key={e} x={lx} y={ly} textAnchor="middle" dominantBaseline="middle"
                  fill={e === currentEmotion ? EMOTION_COLORS[e] : 'rgba(255,255,255,0.4)'}
                  fontSize="9" fontWeight={e === currentEmotion ? 700 : 400}>
                  {EMOTION_ICONS[e]}
                </text>
              );
            })}
          </svg>
        </div>

        {/* Emotion Timeline Bar Chart */}
        <div style={{ background: 'rgba(255,255,255,0.04)', borderRadius: '14px', padding: '14px', display: 'flex', flexDirection: 'column' }}>
          <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', marginBottom: '10px', letterSpacing: '1px' }}>
            EMOTION TIMELINE (live)
          </div>
          <div style={{ flex: 1, display: 'flex', alignItems: 'flex-end', gap: '6px', overflowX: 'auto', paddingBottom: '4px' }}>
            {history.length === 0 ? (
              <div style={{ color: 'rgba(255,255,255,0.3)', fontSize: '0.8rem', margin: 'auto', textAlign: 'center' }}>
                <div style={{ fontSize: '1.5rem', marginBottom: '8px' }}>📊</div>
                Collecting data... (updates every 3s)
              </div>
            ) : (
              history.map((entry, i) => {
                const barColor = EMOTION_COLORS[entry.emotion] || '#00d4ff';
                const barH = Math.max(8, (entry.value / 100) * 70);
                const isLatest = i === history.length - 1;
                return (
                  <div
                    key={i}
                    title={`${entry.emotion} (${entry.value}%) at ${entry.time}`}
                    style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px', flex: '0 0 auto', opacity: isLatest ? 1 : 0.7 + (i / history.length) * 0.3 }}
                  >
                    <div style={{ fontSize: '0.65rem' }}>{EMOTION_ICONS[entry.emotion]}</div>
                    <div style={{
                      width: '22px',
                      height: `${barH}px`,
                      minHeight: '8px',
                      background: isLatest
                        ? barColor
                        : `${barColor}90`,
                      borderRadius: '4px 4px 0 0',
                      transition: 'height 0.5s ease, background 0.3s ease',
                      boxShadow: isLatest ? `0 0 8px ${barColor}60` : undefined,
                    }} />
                    <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.3)', transform: 'rotate(-45deg)', transformOrigin: 'top left', marginTop: '6px', whiteSpace: 'nowrap' }}>
                      {entry.time.split(':').slice(1).join(':')}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* ── Row 3: Stats Summary ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px' }}>
        {statsLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} style={{
              background: 'rgba(255,255,255,0.04)', borderRadius: '12px', padding: '12px',
              textAlign: 'center', border: '1px solid rgba(255,255,255,0.07)', opacity: 0.5,
            }}>
              <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.75rem' }}>Loading...</div>
            </div>
          ))
        ) : stats ? (
          [
            { label: 'Sessions', value: stats.total_sessions ?? 0, icon: '📱' },
            { label: 'Chats', value: stats.total_interactions ?? 0, icon: '💬' },
            { label: 'Memories', value: stats.total_memories ?? 0, icon: '🧠' },
            {
              label: 'Fav Emotion',
              value: `${EMOTION_ICONS[stats.favorite_emotion] || ''} ${stats.favorite_emotion || 'neutral'}`,
              icon: ''
            },
          ].map(s => (
            <div key={s.label} style={{
              background: 'rgba(255,255,255,0.04)', borderRadius: '12px', padding: '12px',
              textAlign: 'center', border: '1px solid rgba(255,255,255,0.07)',
              transition: 'all 0.3s ease',
            }}>
              <div style={{ fontSize: '1.2rem', marginBottom: '4px' }}>{s.icon}</div>
              <div style={{ color: 'white', fontWeight: 700, fontSize: '1.1rem' }}>{s.value}</div>
              <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.7rem' }}>{s.label}</div>
            </div>
          ))
        ) : (
          <div style={{ gridColumn: '1 / -1', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.85rem', padding: '20px' }}>
            Login to view your stats
          </div>
        )}
      </div>

      {/* ── Row 4: Fusion Detail (only shown when fusion data available) ── */}
      {fuseResult && (
        <div style={{ background: 'rgba(255,255,255,0.04)', borderRadius: '14px', padding: '14px', border: '1px solid rgba(255,255,255,0.07)' }}>
          <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', marginBottom: '10px', letterSpacing: '1px' }}>MULTIMODAL FUSION WEIGHTS</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {[
              { label: 'Face', weight: fuseResult.face_weight ?? 0.6, color: faceColor },
              { label: 'Voice', weight: fuseResult.voice_weight ?? 0.4, color: voiceColor },
            ].map(w => (
              <div key={w.label} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ width: '40px', fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)' }}>{w.label}</span>
                <div style={{ flex: 1, background: 'rgba(255,255,255,0.08)', borderRadius: '4px', height: '8px' }}>
                  <div style={{ width: `${Math.round((w.weight ?? 0) * 100)}%`, height: '8px', background: w.color, borderRadius: '4px', transition: 'width 0.8s ease' }} />
                </div>
                <span style={{ width: '36px', fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', textAlign: 'right' }}>
                  {Math.round((w.weight ?? 0) * 100)}%
                </span>
              </div>
            ))}
          </div>
          {fuseResult.ros_behavior && (
            <div style={{ marginTop: '10px', fontSize: '0.75rem', color: 'rgba(255,255,255,0.3)' }}>
              🤖 Robot behavior: <span style={{ color: fusedColor }}>{fuseResult.ros_behavior.animation}</span>
              {' '}at speed <span style={{ color: fusedColor }}>{fuseResult.ros_behavior.speed}x</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AnalyticsDashboard;
