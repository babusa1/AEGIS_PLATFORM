import React, { useEffect, useState, useRef, useCallback } from 'react';
import { SymptomMessageBubble } from '../../components/chat/SymptomMessageBubble';
import { useWebSocket } from '../../hooks/useWebSocket';
import { chatService } from '../../services/chatService';
import type { ChatSession, Message } from '../../types/chat';
import '../../components/chat/SymptomChat.css';

// Send icon SVG
const SendIcon: React.FC = () => (
  <svg viewBox="0 0 24 24" fill="currentColor">
    <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
  </svg>
);

// Plus icon for new chat
const PlusIcon: React.FC = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="12" y1="5" x2="12" y2="19" />
    <line x1="5" y1="12" x2="19" y2="12" />
  </svg>
);

const SymptomChatPage: React.FC = () => {
  const [chatSession, setChatSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isThinking, setIsThinking] = useState(false);
  const [textInput, setTextInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Handle incoming WebSocket messages
  const handleNewMessage = useCallback((wsMessage: any) => {
    console.log('Received WebSocket message:', wsMessage);

    setMessages(prevMessages => {
      // Handle regular message
      if (wsMessage.id) {
        setIsThinking(false);
        
        // Check if this is a completion message
        if (wsMessage.structured_data?.is_complete) {
          setChatSession(prev => prev ? { 
            ...prev, 
            conversation_state: wsMessage.structured_data?.triage_level === 'call_911' ? 'EMERGENCY' : 'COMPLETED' 
          } : null);
        }
        
        return [...prevMessages.filter(m => m.id !== -1 && m.id !== wsMessage.id), wsMessage];
      }
      
      return prevMessages;
    });
  }, []);

  const { isConnected, sendMessage, connectionError } = useWebSocket(
    chatSession?.chat_uuid || null,
    handleNewMessage
  );

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isThinking]);

  // Load today's session
  const loadTodaySession = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await chatService.getTodaySession();
      const sessionData = response.data;
      
      if (!sessionData) {
        throw new Error('No session data returned');
      }
      
      setChatSession(sessionData);
      setMessages(Array.isArray(sessionData.messages) ? sessionData.messages : []);
      setLoading(false);
    } catch (err) {
      setError('Failed to load chat session');
      console.error('Failed to load chat session:', err);
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTodaySession();
  }, []);

  // Start new conversation
  const handleStartNewConversation = async () => {
    try {
      setLoading(true);
      setError(null);
      const sessionData = await chatService.startNewSession();
      setChatSession(sessionData);
      setMessages(Array.isArray(sessionData.messages) ? sessionData.messages : []);
    } catch (err) {
      setError('Failed to start a new chat session');
      console.error('Failed to start a new chat session:', err);
    } finally {
      setLoading(false);
    }
  };

  // Send a message
  const sendUserMessage = (content: string, messageType: Message['message_type'] = 'text') => {
    if (!chatSession || !isConnected) return;

    const userMessage: Message = {
      id: -1,
      chat_uuid: chatSession.chat_uuid,
      sender: 'user',
      message_type: messageType,
      content: content,
      created_at: new Date().toISOString(),
    };
    
    setMessages(prev => [...prev, userMessage]);
    setIsThinking(true);
    sendMessage(content, messageType);
  };

  // Handle option selection (yes/no, single choice)
  const handleOptionSelect = (value: string | boolean) => {
    const content = typeof value === 'boolean' ? (value ? 'Yes' : 'No') : value;
    sendUserMessage(content, 'button_response');
  };

  // Handle multi-select submission
  const handleMultiSelectSubmit = (values: string[]) => {
    const content = values.join(', ');
    sendUserMessage(content, 'multi_select_response');
  };

  // Handle symptom selection
  const handleSymptomSelect = (symptomIds: string[]) => {
    const content = symptomIds.join(', ');
    sendUserMessage(content, 'multi_select_response');
  };

  // Handle text input submission
  const handleTextSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (textInput.trim() && isConnected && !isThinking) {
      sendUserMessage(textInput.trim(), 'text');
      setTextInput('');
    }
  };

  // Determine if we should show text input
  const shouldShowTextInput = () => {
    if (!messages || messages.length === 0) return false;
    if (isThinking) return false;
    
    const lastMessage = messages[messages.length - 1];
    if (lastMessage.sender === 'user') return false;
    
    const frontendType = lastMessage.structured_data?.frontend_type || lastMessage.message_type;
    const phase = lastMessage.structured_data?.phase;
    
    // Always show text input when in ADDING_NOTES phase (personal notes after completion)
    if (phase === 'ADDING_NOTES' || frontendType === 'text_input') {
      return true;
    }
    
    // Don't show input for completed conversations (unless adding notes)
    if (chatSession?.conversation_state === 'COMPLETED' || chatSession?.conversation_state === 'EMERGENCY') {
      return false;
    }
    
    // Show text input for text, number type questions during normal flow
    return frontendType === 'text' || frontendType === 'number';
  };

  // Download summary as text file
  const downloadSummary = () => {
    // Build summary content from messages
    const date = new Date().toLocaleDateString('en-US', { 
      year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit'
    });
    
    let summaryText = `SYMPTOM CHECK SUMMARY\n`;
    summaryText += `${'='.repeat(50)}\n`;
    summaryText += `Date: ${date}\n\n`;
    
    // Extract symptoms from chat session
    if (chatSession?.symptom_list && chatSession.symptom_list.length > 0) {
      summaryText += `SYMPTOMS REPORTED:\n`;
      chatSession.symptom_list.forEach((symptom: string) => {
        summaryText += `  • ${symptom.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}\n`;
      });
      summaryText += `\n`;
    }
    
    // Add conversation history
    summaryText += `CONVERSATION LOG:\n`;
    summaryText += `${'-'.repeat(50)}\n`;
    messages.forEach(msg => {
      const sender = msg.sender === 'user' ? 'You' : 'Ruby';
      const time = new Date(msg.created_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
      // Clean up content - remove markdown formatting
      const content = msg.content
        .replace(/\*\*/g, '')
        .replace(/\n{3,}/g, '\n\n');
      summaryText += `[${time}] ${sender}:\n${content}\n\n`;
    });
    
    // Add footer
    summaryText += `${'-'.repeat(50)}\n`;
    summaryText += `Generated by OncoLife Symptom Checker\n`;
    summaryText += `This is not a medical diagnosis. Please consult your healthcare provider.\n`;
    
    // Create and trigger download
    const blob = new Blob([summaryText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `symptom-check-${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Check if message should show interactive elements
  const shouldShowInteractive = (message: Message, index: number): boolean => {
    if (message.sender !== 'assistant') return false;
    if (isThinking) return false;
    
    // Only show for the last assistant message if no user response after
    for (let i = index + 1; i < messages.length; i++) {
      if (messages[i].sender === 'user') {
        return false;
      }
    }
    
    return true;
  };

  // Render thinking indicator
  const renderThinkingIndicator = () => (
    <div className="message-wrapper assistant">
      <div className="message-with-avatar">
        <div className="mini-avatar">💎</div>
        <div className="thinking-indicator">
          <div className="thinking-dots">
            <div className="thinking-dot" />
            <div className="thinking-dot" />
            <div className="thinking-dot" />
          </div>
          <span className="thinking-text">Ruby is thinking...</span>
        </div>
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="symptom-chat-container">
        <div className="connection-overlay">
          <div className="connection-spinner" />
          <span className="connection-text">Loading symptom checker...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="symptom-chat-container">
        <div className="connection-overlay">
          <span className="connection-text">Error: {error}</span>
          <button className="retry-btn" onClick={loadTodaySession}>Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="symptom-chat-container">
      {/* Header */}
      <div className="symptom-chat-header">
        <div className="header-left">
          <div className="ruby-avatar">💎</div>
          <div className="header-info">
            <h1>Ruby - Symptom Checker</h1>
            <div className="header-status">
              <span className="status-dot" />
              <span>Online • Here to help</span>
            </div>
          </div>
        </div>
        <div className="header-right">
          <button className="new-chat-btn" onClick={handleStartNewConversation}>
            <PlusIcon />
            <span>New Check-in</span>
          </button>
          <button 
            className="exit-chat-btn" 
            onClick={() => window.location.href = '/'}
            title="Exit Chat"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Connection status */}
      {!isConnected && !connectionError && (
        <div className="connection-overlay">
          <div className="connection-spinner" />
          <span className="connection-text">Connecting to Ruby...</span>
        </div>
      )}

      {connectionError && (
        <div className="connection-error-banner">
          <span>⚠️ {connectionError}</span>
          <button className="retry-btn" onClick={() => window.location.reload()}>
            Retry
          </button>
        </div>
      )}

      {/* Messages */}
      <div className="symptom-messages-container">
        {messages.map((message, index) => (
          <SymptomMessageBubble
            key={`${message.id}-${index}`}
            message={message}
            onOptionSelect={handleOptionSelect}
            onMultiSelectSubmit={handleMultiSelectSubmit}
            onSymptomSelect={handleSymptomSelect}
            onDisclaimerAccept={() => handleOptionSelect('accept')}
            onEmergencyCheck={(selected) => {
              // Send emergency selection - 'none' or array of selected symptoms
              const content = selected.join(', ') || 'none';
              sendUserMessage(content, 'button_response');
            }}
            onSummaryAction={(action) => {
              // Handle download action
              if (action === 'download') {
                downloadSummary();
              }
              // Send message to backend for other actions
              sendUserMessage(action, 'button_response');
            }}
            shouldShowInteractive={shouldShowInteractive(message, index)}
          />
        ))}
        {isThinking && renderThinkingIndicator()}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      {shouldShowTextInput() && (
        <div className="symptom-input-container">
          <form onSubmit={handleTextSubmit} className="input-wrapper">
            <input
              type="text"
              className="text-input"
              placeholder="Type your response..."
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              disabled={!isConnected || isThinking}
            />
            <button 
              type="submit" 
              className="send-btn"
              disabled={!textInput.trim() || !isConnected || isThinking}
            >
              <SendIcon />
            </button>
          </form>
        </div>
      )}
    </div>
  );
};

export default SymptomChatPage;





