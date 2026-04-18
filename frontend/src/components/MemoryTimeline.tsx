import React, { useEffect, useState } from 'react';
import { useAuthStore } from '../store/authStore';

const EMOTION_ICONS: Record<string, string> = {
  happy: '😊', sad: '😢', angry: '😠', fearful: '😨',
  surprised: '😲', disgust: '🤢', calm: '😌', neutral: '🤖',
};

const EMOTION_COLORS: Record<string, string> = {
  happy: '#ffd700', sad: '#4169e1', angry: '#ff4444',
  fearful: '#9400d3', surprised: '#ff8c00', calm: '#00ced1', neutral: '#00d4ff',
};

interface MemoryItem {
  id: number;
  text: string;
  emotion: string;
  timestamp: string;
  importance: string | number;
}

type Filter = 'all' | 'today' | 'session';

interface MemoryTimelineProps {
  onHighlightMemory?: (memoryId: number) => void;
}

const MemoryTimeline: React.FC<MemoryTimelineProps> = ({ onHighlightMemory }) => {
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [filter, setFilter] = useState<Filter>('all');
  const [search, setSearch] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);
  const token = useAuthStore((s) => s.token);

  const fetchMemories = async () => {
    setIsLoading(true);
    setError(false);
    try {
      const resp = await fetch('http://localhost:8000/api/memory/recent', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!resp.ok) throw new Error('API error');
      const data = await resp.json();
      setMemories(data.memories || []);
    } catch {
      setError(true);
      // Fallback stub only shown on connection error
      setMemories([
        { id: 1, text: 'User mentioned they love coffee ☕', emotion: 'happy', timestamp: new Date().toISOString(), importance: 'high' },
        { id: 2, text: 'User talked about project deadline stress', emotion: 'fearful', timestamp: new Date(Date.now() - 3600000).toISOString(), importance: 'medium' },
        { id: 3, text: 'User enjoys evening walks', emotion: 'calm', timestamp: new Date(Date.now() - 7200000).toISOString(), importance: 'low' },
        { id: 4, text: 'User excited about new sci-fi movie', emotion: 'surprised', timestamp: new Date(Date.now() - 10800000).toISOString(), importance: 'low' },
        { id: 5, text: 'Feeling stressed about team presentation', emotion: 'angry', timestamp: new Date(Date.now() - 14400000).toISOString(), importance: 'high' },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  // Fetch on mount and auto-refresh every 30 seconds
  useEffect(() => {
    fetchMemories();
    const autoRefresh = setInterval(fetchMemories, 30000);
    return () => clearInterval(autoRefresh);
  }, [token]);

  const now = new Date();
  const filtered = memories.filter((m) => {
    const matchSearch = m.text.toLowerCase().includes(search.toLowerCase());
    if (!matchSearch) return false;
    if (filter === 'today') {
      const d = new Date(m.timestamp);
      return d.getDate() === now.getDate() && d.getMonth() === now.getMonth();
    }
    if (filter === 'session') {
      const d = new Date(m.timestamp);
      return now.getTime() - d.getTime() < 3600000;
    }
    return true;
  });

  const importanceColor = (imp: string | number) => {
    if (imp === 'high' || imp === 2) return '#ff4444';
    if (imp === 'medium' || imp === 1) return '#ff8c00';
    return '#00d4ff';
  };

  return (
    <div style={{ padding: '20px', height: '100%', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Search bar */}
      <div style={{ position: 'relative' }}>
        <input
          id="memory-search-input"
          type="text"
          placeholder="🔍  Search memories..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{
            width: '100%', padding: '10px 16px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.1)',
            background: 'rgba(0,0,0,0.3)', color: 'white', fontSize: '0.9rem', outline: 'none',
            boxSizing: 'border-box',
          }}
        />
      </div>

      {/* Filter buttons */}
      <div style={{ display: 'flex', gap: '8px' }}>
        {(['all', 'today', 'session'] as Filter[]).map((f) => (
          <button
            key={f}
            id={`memory-filter-${f}`}
            onClick={() => setFilter(f)}
            style={{
              padding: '6px 16px', borderRadius: '20px', border: 'none', cursor: 'pointer',
              background: filter === f ? '#00d4ff' : 'rgba(255,255,255,0.1)',
              color: filter === f ? 'black' : 'rgba(255,255,255,0.7)',
              fontSize: '0.8rem', fontWeight: 600,
              transition: 'all 0.2s ease',
            }}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
        <button
          onClick={fetchMemories}
          style={{
            marginLeft: 'auto', padding: '6px 12px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.1)',
            background: 'transparent', color: 'rgba(255,255,255,0.5)', fontSize: '0.75rem', cursor: 'pointer',
          }}
        >
          ↻ Refresh
        </button>
      </div>

      {/* Timeline */}
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0' }}>
        {isLoading ? (
          <div style={{ textAlign: 'center', color: 'rgba(255,255,255,0.4)', marginTop: '40px' }}>
            Loading memories...
          </div>
        ) : filtered.length === 0 ? (
          <div style={{ textAlign: 'center', color: 'rgba(255,255,255,0.4)', marginTop: '40px' }}>
            {error
              ? <><div style={{ fontSize: '1.5rem', marginBottom: '8px' }}>⚠️</div>Backend offline — showing sample data</>
              : <><div style={{ fontSize: '1.5rem', marginBottom: '8px' }}>🌙</div>No memories yet — start chatting!</>
            }
          </div>
        ) : (
          filtered.map((memory, idx) => {
            const color = EMOTION_COLORS[memory.emotion] || '#00d4ff';
            const icon = EMOTION_ICONS[memory.emotion] || '🤖';
            const impColor = importanceColor(memory.importance);
            const date = new Date(memory.timestamp);
            return (
              <div key={memory.id} style={{ display: 'flex', gap: '12px', position: 'relative', paddingBottom: '4px' }}>
                {/* Timeline line */}
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '24px', flexShrink: 0 }}>
                  <div style={{
                    width: '28px', height: '28px', borderRadius: '50%',
                    background: `${color}25`, border: `2px solid ${color}`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: '0.9rem', flexShrink: 0, marginTop: '12px',
                    boxShadow: `0 0 8px ${color}40`,
                  }}>
                    {icon}
                  </div>
                  {idx < filtered.length - 1 && (
                    <div style={{ width: '2px', flex: 1, background: 'rgba(255,255,255,0.08)', minHeight: '24px' }} />
                  )}
                </div>

                {/* Memory card */}
                <div
                  onClick={() => onHighlightMemory?.(memory.id)}
                  style={{
                    flex: 1, background: 'rgba(255,255,255,0.04)',
                    border: `1px solid rgba(255,255,255,0.08)`,
                    borderLeft: `3px solid ${color}`,
                    borderRadius: '12px',
                    padding: '12px 14px',
                    margin: '8px 0',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.08)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.04)')}
                >
                  <p style={{ margin: '0 0 8px 0', color: 'white', fontSize: '0.88rem', lineHeight: 1.5 }}>
                    {memory.text}
                  </p>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                      <span style={{
                        fontSize: '0.7rem', padding: '2px 8px', borderRadius: '10px',
                        background: `${color}20`, color, border: `1px solid ${color}40`,
                      }}>
                        {memory.emotion}
                      </span>
                      <span style={{
                        fontSize: '0.7rem', padding: '2px 8px', borderRadius: '10px',
                        background: `${impColor}20`, color: impColor,
                      }}>
                        {memory.importance}
                      </span>
                    </div>
                    <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.35)' }}>
                      {date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default MemoryTimeline;
