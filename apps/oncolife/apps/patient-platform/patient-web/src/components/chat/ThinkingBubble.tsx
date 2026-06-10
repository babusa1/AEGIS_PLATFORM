import React from 'react';
import './ThinkingBubble.css';

export const ThinkingBubble: React.FC = () => (
  <div className="message-bubble assistant">
    <div className="typing-indicator">
      <span></span>
      <span></span>
      <span></span>
    </div>
  </div>
); 