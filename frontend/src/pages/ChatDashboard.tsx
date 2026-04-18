import React from 'react';
import ChatPanel from '../components/ChatPanel';
import EmotionCamera from '../components/EmotionCamera';
import '../styles/Chat.css';

const ChatDashboard: React.FC = () => {
  return (
    <div className="dashboard-container">
      <div className="left-panel">
        <ChatPanel />
      </div>
      <div className="right-panel">
        <EmotionCamera />
        <div className="robot-container">
          <h2>Robot 3D World (Coming Soon)</h2>
          <p>Member 4 will integrate the React Three Fiber models here seamlessly!</p>
        </div>
      </div>
    </div>
  );
};

export default ChatDashboard;
