import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';

import { motion } from 'framer-motion';
import { Loader2 } from 'lucide-react';
import { API_BASE_URL } from '../config';
import '../styles/Auth.css';

const Signup: React.FC = () => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  
  const navigate = useNavigate();

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to register account');
      }

      // Automatically redirect to login on success
      navigate('/login');
    } catch (err: any) {
      setError(err.message || 'Registration failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <motion.div 
        className="glass-card"
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
      >
        <h1>Initialize Profile</h1>
        <p>Begin your journey with the Chat Robot.</p>
        
        {error && <div className="auth-error">{error}</div>}
        
        <form onSubmit={handleSignup}>
          <div className="input-group">
            <label>Username</label>
            <input 
              type="text" 
              placeholder="e.g. RobotFan2026" 
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required 
            />
          </div>

          <div className="input-group">
            <label>Email ID</label>
            <input 
              type="email" 
              placeholder="user@example.com" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required 
            />
          </div>
          
          <div className="input-group">
            <label>Password</label>
            <input 
              type="password" 
              placeholder="Create a strong password" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required 
            />
          </div>
          
          <button type="submit" className="auth-button" disabled={isLoading}>
            {isLoading ? <Loader2 className="animate-spin inline" size={20} /> : 'Register'}
          </button>
        </form>
        
        <div className="auth-footer">
          Already verified? <Link to="/login">Sign in here</Link>
        </div>
      </motion.div>
    </div>
  );
};

export default Signup;
