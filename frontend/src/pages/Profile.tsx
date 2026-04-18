import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { LogOut, Edit2, Save, X } from 'lucide-react';
import { API_BASE_URL } from '../config';

const EMOTION_ICONS: Record<string, string> = {
  happy: '😊', sad: '😢', angry: '😠', fearful: '😨',
  surprised: '😲', disgust: '🤢', calm: '😌', neutral: '🤖',
};

const AVATAR_OPTIONS = ['🤖', '👽', '🦾', '🧠', '🎭', '🌊', '⚡', '🔥'];

const Profile: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editEmail, setEditEmail] = useState('');
  const [selectedAvatar, setSelectedAvatar] = useState('🤖');
  const [isSaving, setIsSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState('');

  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();

  useEffect(() => {
    if (!token) return;
    fetch(`${API_BASE_URL}/api/user/stats`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
      .then(data => {
        setStats(data);
        setEditEmail('');
      })
      .catch(() => {});
  }, [token]);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await fetch(`${API_BASE_URL}/api/auth/profile`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ email: editEmail || undefined, avatar: selectedAvatar }),
      });
      setSaveMsg('Profile updated ✅');
      setIsEditing(false);
    } catch { setSaveMsg('Failed to save ❌'); }
    finally { setIsSaving(false); setTimeout(() => setSaveMsg(''), 2500); }
  };

  const handleLogout = () => { logout(); navigate('/login'); };

  const emotionBreakdown = stats?.emotion_breakdown || { happy: 12, neutral: 8, sad: 3, surprised: 5, calm: 4 };
  const totalEmotions = Object.values(emotionBreakdown).reduce<number>((a: number, b) => a + (b as number), 0);

  return (
    <div style={{ padding: '24px', maxWidth: '700px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {/* Profile Header */}
      <div style={{
        background: 'rgba(255,255,255,0.05)', borderRadius: '20px',
        border: '1px solid rgba(255,255,255,0.1)',
        padding: '28px', textAlign: 'center', position: 'relative',
      }}>
        {/* Avatar */}
        <div style={{
          width: '90px', height: '90px', borderRadius: '50%', margin: '0 auto 16px',
          background: 'linear-gradient(135deg, rgba(0,212,255,0.2), rgba(255,0,150,0.2))',
          border: '3px solid rgba(0,212,255,0.5)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '2.8rem',
          boxShadow: '0 0 30px rgba(0,212,255,0.2)',
        }}>
          {selectedAvatar}
        </div>

        <h2 style={{ margin: '0 0 4px', color: 'white', fontSize: '1.4rem' }}>{user?.username}</h2>
        <p style={{ margin: '0 0 16px', color: 'rgba(255,255,255,0.4)', fontSize: '0.85rem' }}>
          Member since {stats?.member_since || '2026-04-17'}
        </p>

        {/* Edit/Save buttons */}
        <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
          {!isEditing ? (
            <button id="edit-profile-btn" onClick={() => setIsEditing(true)} style={{
              display: 'flex', alignItems: 'center', gap: '6px',
              padding: '8px 18px', borderRadius: '12px', border: '1px solid rgba(0,212,255,0.4)',
              background: 'rgba(0,212,255,0.1)', color: '#00d4ff', cursor: 'pointer', fontSize: '0.85rem',
            }}>
              <Edit2 size={14} /> Edit Profile
            </button>
          ) : (
            <>
              <button onClick={handleSave} disabled={isSaving} style={{
                display: 'flex', alignItems: 'center', gap: '6px',
                padding: '8px 18px', borderRadius: '12px', border: 'none',
                background: '#00d4ff', color: 'black', cursor: 'pointer', fontWeight: 600, fontSize: '0.85rem',
              }}>
                <Save size={14} /> {isSaving ? 'Saving...' : 'Save'}
              </button>
              <button onClick={() => setIsEditing(false)} style={{
                display: 'flex', alignItems: 'center', gap: '6px',
                padding: '8px 14px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.15)',
                background: 'transparent', color: 'white', cursor: 'pointer', fontSize: '0.85rem',
              }}>
                <X size={14} /> Cancel
              </button>
            </>
          )}
          <button id="logout-btn" onClick={handleLogout} style={{
            display: 'flex', alignItems: 'center', gap: '6px',
            padding: '8px 18px', borderRadius: '12px', border: '1px solid rgba(255,68,68,0.4)',
            background: 'rgba(255,68,68,0.1)', color: '#ff4444', cursor: 'pointer', fontSize: '0.85rem',
          }}>
            <LogOut size={14} /> Logout
          </button>
        </div>
        {saveMsg && <div style={{ marginTop: '12px', color: '#00ff88', fontSize: '0.85rem' }}>{saveMsg}</div>}
      </div>

      {/* Edit Form */}
      {isEditing && (
        <div style={{
          background: 'rgba(255,255,255,0.05)', borderRadius: '16px',
          border: '1px solid rgba(255,255,255,0.1)', padding: '20px',
          display: 'flex', flexDirection: 'column', gap: '16px',
        }}>
          <div>
            <label style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.8rem', display: 'block', marginBottom: '6px' }}>New Email</label>
            <input
              id="profile-email-input"
              type="email" placeholder="new@email.com"
              value={editEmail} onChange={(e) => setEditEmail(e.target.value)}
              style={{
                width: '100%', padding: '10px 14px', borderRadius: '10px',
                border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(0,0,0,0.3)',
                color: 'white', fontSize: '0.9rem', outline: 'none', boxSizing: 'border-box',
              }}
            />
          </div>
          <div>
            <label style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.8rem', display: 'block', marginBottom: '8px' }}>Avatar</label>
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
              {AVATAR_OPTIONS.map(av => (
                <button key={av} onClick={() => setSelectedAvatar(av)} style={{
                  width: '44px', height: '44px', borderRadius: '50%', fontSize: '1.4rem', cursor: 'pointer',
                  border: selectedAvatar === av ? '2px solid #00d4ff' : '2px solid transparent',
                  background: selectedAvatar === av ? 'rgba(0,212,255,0.15)' : 'rgba(255,255,255,0.07)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  transition: 'all 0.2s ease',
                }}>
                  {av}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Stats Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
        {[
          { label: 'Total Sessions', value: stats?.total_sessions ?? '-', icon: '📱' },
          { label: 'Interactions', value: stats?.total_interactions ?? '-', icon: '💬' },
          { label: 'Memories', value: stats?.total_memories ?? '-', icon: '🧠' },
        ].map(s => (
          <div key={s.label} style={{
            background: 'rgba(255,255,255,0.05)', borderRadius: '16px',
            border: '1px solid rgba(255,255,255,0.08)', padding: '18px',
            textAlign: 'center',
          }}>
            <div style={{ fontSize: '1.8rem', marginBottom: '8px' }}>{s.icon}</div>
            <div style={{ color: 'white', fontSize: '1.6rem', fontWeight: 700 }}>{s.value}</div>
            <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.75rem', marginTop: '4px' }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Emotion Distribution */}
      <div style={{
        background: 'rgba(255,255,255,0.05)', borderRadius: '16px',
        border: '1px solid rgba(255,255,255,0.08)', padding: '20px',
      }}>
        <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.75rem', letterSpacing: '1px', marginBottom: '16px' }}>
          EMOTION DISTRIBUTION
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {Object.entries(emotionBreakdown).map(([emotion, count]) => {
            const pct = Math.round(((count as number) / totalEmotions) * 100);
            const color = { happy: '#ffd700', neutral: '#00d4ff', sad: '#4169e1', surprised: '#ff8c00', calm: '#00ced1', angry: '#ff4444', fearful: '#9400d3' }[emotion] || '#00d4ff';
            return (
              <div key={emotion} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ width: '20px', textAlign: 'center' }}>{EMOTION_ICONS[emotion]}</span>
                <div style={{ flex: 1, background: 'rgba(255,255,255,0.08)', borderRadius: '6px', height: '10px' }}>
                  <div style={{ width: `${pct}%`, height: '10px', background: color, borderRadius: '6px', transition: 'width 0.8s ease' }} />
                </div>
                <span style={{ width: '28px', textAlign: 'right', color: 'rgba(255,255,255,0.5)', fontSize: '0.75rem' }}>{pct}%</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Favorite Emotion */}
      {stats?.favorite_emotion && (
        <div style={{
          background: 'rgba(255,255,255,0.05)', borderRadius: '16px',
          border: '1px solid rgba(255,255,255,0.08)', padding: '16px',
          display: 'flex', alignItems: 'center', gap: '16px',
        }}>
          <div style={{ fontSize: '2.5rem' }}>{EMOTION_ICONS[stats.favorite_emotion]}</div>
          <div>
            <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.75rem' }}>MOST COMMON EMOTION</div>
            <div style={{ color: 'white', fontSize: '1.2rem', fontWeight: 600, textTransform: 'uppercase', marginTop: '4px' }}>
              {stats.favorite_emotion}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Profile;
