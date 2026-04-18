import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { motion } from 'framer-motion';
import { Loader2, Eye, EyeOff } from 'lucide-react';
import { API_BASE_URL } from '../config';
import '../styles/Auth.css';

const Login: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPass, setShowPass] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const setToken = useAuthStore((state) => state.setToken);
  const setUser = useAuthStore((state) => state.setUser);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      // Step 1 — Authenticate and get JWT
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || 'Invalid username or password');
      }

      const data = await response.json();
      const token = data.access_token;
      setToken(token);

      // Step 2 — Fetch real user profile to get email, avatar etc.
      try {
        const profileResp = await fetch(`${API_BASE_URL}/api/auth/profile?token=${token}`);
        if (profileResp.ok) {
          const profile = await profileResp.json();
          setUser({ username: profile.username, email: profile.email, avatar: profile.avatar, id: profile.id });
        } else {
          setUser({ username });
        }
      } catch {
        setUser({ username });
      }

      navigate('/chat');
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <motion.div
        className="glass-card"
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
      >
        {/* Logo/Icon */}
        <div style={{ textAlign: 'center', fontSize: '3rem', marginBottom: '8px' }}>🤖</div>
        <h1>Welcome Back</h1>
        <p>Your Emotion-Aware Robot is waiting.</p>

        {error && <div className="auth-error" id="login-error">{error}</div>}

        <form onSubmit={handleLogin}>
          <div className="input-group">
            <label htmlFor="login-username">Username</label>
            <input
              id="login-username"
              type="text"
              placeholder="Enter your username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoComplete="username"
            />
          </div>

          <div className="input-group" style={{ position: 'relative' }}>
            <label htmlFor="login-password">Password</label>
            <input
              id="login-password"
              type={showPass ? 'text' : 'password'}
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              style={{ paddingRight: '44px' }}
            />
            <button
              type="button"
              onClick={() => setShowPass(!showPass)}
              style={{
                position: 'absolute', right: '12px', bottom: '12px',
                background: 'none', border: 'none', color: 'rgba(255,255,255,0.4)',
                cursor: 'pointer', padding: '0', display: 'flex',
              }}
            >
              {showPass ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>

          <button id="login-submit-btn" type="submit" className="auth-button" disabled={isLoading}>
            {isLoading
              ? <><Loader2 size={18} style={{ display: 'inline', animation: 'spinAnim 1s linear infinite', marginRight: '8px' }} /> Authenticating...</>
              : 'Login →'
            }
          </button>
        </form>

        <div className="auth-footer">
          Don't have an account? <Link to="/signup">Create Profile</Link>
        </div>
      </motion.div>

      <style>{`@keyframes spinAnim { from{transform:rotate(0deg)}to{transform:rotate(360deg)} }`}</style>
    </div>
  );
};

export default Login;
