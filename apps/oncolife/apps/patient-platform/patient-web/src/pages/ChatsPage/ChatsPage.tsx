/**
 * =============================================================================
 * Symptom Checker Chat Page - Patient Portal
 * =============================================================================
 * 
 * Module:      ChatsPage.tsx
 * Description: Daily symptom check-in chat interface. Implements the 7-phase
 *              symptom checker flow with real-time WebSocket communication.
 * 
 * Created:     2025-12-15
 * Modified:    2026-01-16
 * Author:      Naveen Babu S A
 * Version:     2.1.0
 * 
 * Features:
 *   - WebSocket-based real-time chat with Ruby (AI assistant)
 *   - 7-phase symptom triage flow
 *   - Button-based responses with validation
 *   - Calendar integration for dates
 *   - Severity assessment and escalation detection
 * 
 * Copyright:
 *   (c) 2026 OncoLife Health Technologies. All rights reserved.
 * =============================================================================
 */

import React, { useEffect, useState, useRef, useCallback } from 'react';
import { MessageBubble } from '../../components/chat/MessageBubble';
import { MessageInput } from '../../components/chat/MessageInput';
import { ThinkingBubble } from '../../components/chat/ThinkingBubble';
import { CalendarModal } from '../../components/chat/CalendarModal';
import { useWebSocket } from '../../hooks/useWebSocket';
import { useSymptomList } from '../../hooks/useSymptomList';
import { chatService } from '../../services/chatService';
import { getTodayInUserTimezone } from '@oncolife/shared-utils';
import type { ChatSession, Message } from '../../types/chat';
import '../../components/chat/Chat.css';
import { API_CONFIG } from '../../config/api';

const ChatsPage: React.FC = () => {
  const [chatSession, setChatSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isThinking, setIsThinking] = useState(false);
  const [isCalendarModalOpen, setIsCalendarModalOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Use the symptom list hook for localStorage management
  const { 
    symptomList, 
    updateSymptomList, 
    addSymptoms, 
    resetSymptomList 
  } = useSymptomList();

  const handleNewMessage = useCallback((wsMessage: any) => {
    console.log('Received WebSocket message:', wsMessage);

    setMessages(prevMessages => {
      if (wsMessage.type === 'message_chunk') {
        console.log('Processing message chunk:', wsMessage);
        setIsThinking(false);
        const messageIndex = prevMessages.findIndex(m => m.id === wsMessage.message_id);
        if (messageIndex !== -1) {
          const updatedMessages = [...prevMessages];
          updatedMessages[messageIndex].content += wsMessage.content;
          return updatedMessages;
        } else {
          const newMessage: Message = {
            id: wsMessage.message_id,
            chat_uuid: chatSession?.chat_uuid || '',
            sender: 'assistant',
            message_type: 'text',
            content: wsMessage.content,
            created_at: new Date().toISOString(),
          };
          return [...prevMessages, newMessage];
        }
      } else if (wsMessage.type === 'message_end') {
        console.log('Processing message end:', wsMessage);
        setIsThinking(false);
        return prevMessages;
      } else if (wsMessage.id) {
        console.log('Processing complete message:', wsMessage);
        setIsThinking(false);
        
        // Check if this is a final summary message (indicates conversation completion)
        if (wsMessage.content && wsMessage.content.includes('Thank you for completing this chat!')) {
          // Update the chat session state to COMPLETED
          setChatSession(prev => prev ? { ...prev, conversation_state: 'COMPLETED' } : null);
        }
        
        // Check for new symptoms in the LLM response
        if (wsMessage.content && typeof wsMessage.content === 'string') {
          try {
            // Try to parse the content as JSON to extract new_symptoms
            const contentStr = wsMessage.content.trim();
            if (contentStr.startsWith('{') && contentStr.endsWith('}')) {
              const parsedContent = JSON.parse(contentStr);
              if (parsedContent.new_symptoms && Array.isArray(parsedContent.new_symptoms)) {
                console.log('New symptoms detected from LLM:', parsedContent.new_symptoms);
                // Add new symptoms to localStorage
                addSymptoms(parsedContent.new_symptoms);
              }
            }
          } catch (error) {
            // Content is not JSON, continue normally
            console.log('Message content is not JSON, processing as normal text');
          }
        }
        
        return [...prevMessages.filter(m => m.id !== -1 && m.id !== wsMessage.id), wsMessage];
      }
      console.log('No matching message type, returning previous messages');
      return prevMessages;
    });
  }, [chatSession, addSymptoms]);

  const { isConnected, sendMessage, connectionError } = useWebSocket(
    chatSession?.chat_uuid || null,
    handleNewMessage
  );

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadTodaySession = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await chatService.getTodaySession();
      // Gateway now returns the backend payload directly under response.data
      const sessionData = response.data;
      
      if (!sessionData) {
        throw new Error('No session data returned');
      }
      
      // Set chat session immediately to start WebSocket connection
      setChatSession(sessionData);
      
      // Set messages after session is set (guard against undefined)
      setMessages(Array.isArray(sessionData.messages) ? sessionData.messages : []);
      
      // Update symptom list in localStorage based on backend response
      if (sessionData.symptom_list && Array.isArray(sessionData.symptom_list)) {
        console.log('Loading symptom list from backend:', sessionData.symptom_list);
        updateSymptomList(sessionData.symptom_list);
      } else {
        console.log('No symptom list from backend, resetting to empty');
        resetSymptomList();
      }
      
      // Stop loading once we have session data (don't wait for WebSocket)
      setLoading(false);
    } catch (error) {
      setError('Failed to load chat session');
      console.error('Failed to load chat session:', error);
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTodaySession();
  }, []);

  const handleStartNewConversation = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Reset symptom list in localStorage for new conversation
      resetSymptomList();
      
      const sessionData = await chatService.startNewSession();
      setChatSession(sessionData);
      setMessages(Array.isArray(sessionData.messages) ? sessionData.messages : []);
      
      // Ensure symptom list is empty for new conversation
      if (sessionData.symptom_list && Array.isArray(sessionData.symptom_list)) {
        updateSymptomList(sessionData.symptom_list);
      }
    } catch (error) {
      setError('Failed to start a new chat session');
      console.error('Failed to start a new chat session:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSendMessage = (content: string) => {
    if (!chatSession) return;
    const userMessage: Message = {
      id: -1,
      chat_uuid: chatSession.chat_uuid,
      sender: 'user',
      message_type: 'text',
      content: content,
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);
    if (isConnected) {
      setIsThinking(true);
      sendMessage(content, 'text');
    }
  };

  const handleButtonClick = async (option: string) => {
    if (!chatSession) return;
    // Handle special chemo date responses
    if (option === "I had it recently, but didn't record it") {
      setIsCalendarModalOpen(true);
      return;
    }

    if (option === "Yes" && messages.length > 0) {
      // Check if this is the first question about chemotherapy
      const lastMessage = messages[messages.length - 1];
      console.log('[CHEMO DEBUG] Last message content:', lastMessage.content);
      console.log('[CHEMO DEBUG] Checking if contains "chemotherapy today":', lastMessage.content.toLowerCase().includes('chemotherapy today'));
      console.log('[CHEMO DEBUG] Checking if contains "did you get chemotherapy":', lastMessage.content.toLowerCase().includes('did you get chemotherapy'));
      
      if (lastMessage.content.toLowerCase().includes('did you get chemotherapy')) {
        try {
          console.log('[CHEMO DEBUG] Attempting to log chemotherapy date for today');
          // Get today's date in user's timezone
          const todayInUserTz = getTodayInUserTimezone();
          console.log('[CHEMO DEBUG] Today in user timezone:', todayInUserTz.toISOString().split('T')[0]);
          
          const chemoResult = await chatService.logChemoDate(todayInUserTz);
          console.log('[CHEMO DEBUG] Successfully logged chemotherapy date for today:', chemoResult);
        } catch (error) {
          console.error('[CHEMO DEBUG] Failed to log chemotherapy date:', error);
          // Don't throw the error, just log it and continue with the chat
        }
      } else {
        console.log('[CHEMO DEBUG] Condition not met - not logging chemo date');
      }
    }

    // Regular message handling
    const userMessage: Message = {
      id: -1,
      chat_uuid: chatSession.chat_uuid,
      sender: 'user',
      message_type: 'button_response',
      content: option,
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);
    if (isConnected) {
      setIsThinking(true);
      sendMessage(option, 'button_response');
    }
  };

  const handleMultiSelectSubmit = (selections: string[]) => {
    if (!chatSession) return;
    
    // Filter out "None" selection and store symptoms in localStorage
    const validSelections = selections.filter(s => s.toLowerCase() !== 'none');
    if (validSelections.length > 0) {
      console.log('Storing selected symptoms:', validSelections);
      updateSymptomList(validSelections);
    } else {
      console.log('No valid symptoms selected, resetting symptom list');
      resetSymptomList();
    }
    
    const formattedSelections = selections.join(', ');
    const userMessage: Message = {
      id: -1,
      chat_uuid: chatSession.chat_uuid,
      sender: 'user',
      message_type: 'multi_select_response',
      content: formattedSelections,
      created_at: new Date().toISOString(),
    };
    
    setMessages(prev => {
        const newMessages = [...prev];
        let latestAssistantMsgIndex = -1;
        for (let i = newMessages.length - 1; i >= 0; i--) {
            if (newMessages[i].sender === 'assistant') {
                latestAssistantMsgIndex = i;
                break;
            }
        }
        
        if (latestAssistantMsgIndex > -1) {
            newMessages[latestAssistantMsgIndex] = {
                ...newMessages[latestAssistantMsgIndex],
                structured_data: {
                    ...newMessages[latestAssistantMsgIndex].structured_data,
                    selected_options: selections
                }
            };
        }
        return [...newMessages, userMessage];
    });

    if (isConnected) {
      setIsThinking(true);
      sendMessage(formattedSelections, 'multi_select_response');
    }
  };

  const handleFeelingSelect = (feeling: string) => {
    if (!chatSession) return;
    // Optimistically add the user's feeling selection as a message
    const userMessage: Message = {
      id: -1,
      chat_uuid: chatSession.chat_uuid,
      sender: 'user',
      message_type: 'feeling_response',
      content: feeling,
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);

    // Persist overall feeling to backend
    fetch(`${API_CONFIG.BASE_URL}/chat/${chatSession.chat_uuid}/feeling`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('authToken') || ''}`
      },
      body: JSON.stringify({ feeling })
    }).catch(() => {});

    // Send the feeling to the backend via WS to continue flow
    if (isConnected) {
      setIsThinking(true);
      sendMessage(feeling, 'feeling_response');
    }
  };

  const handleCalendarDateSelect = async (selectedDate: Date) => {
    if (!chatSession) return;
    // Format the date for display in user's timezone
    const dateString = selectedDate.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });

    // Optimistically add the message so the UI updates immediately
    const userMessage: Message = {
      id: -1,
      chat_uuid: chatSession.chat_uuid,
      sender: 'user',
      message_type: 'button_response',
      content: `Yes, I got chemotherapy on ${dateString}`,
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);

    if (isConnected) {
      setIsThinking(true);
      sendMessage(`Yes, I got chemotherapy on ${dateString}`, 'button_response');
    }

    // Fire-and-forget the API persistence (log errors but don't block the UI)
    try {
      await chatService.logChemoDate(selectedDate);
      console.log('Logged chemotherapy date:', selectedDate);
    } catch (error) {
      console.error('Failed to log chemotherapy date:', error);
    }
  };

  const shouldShowTextInput = () => {
    // Never show input if the conversation is over
    if (chatSession?.conversation_state === 'COMPLETED' || chatSession?.conversation_state === 'EMERGENCY') {
      return false;
    }
    
    if (!messages || messages.length === 0) return true;
    const lastMessage = messages[messages.length - 1];
    if (isThinking) return false;
    if (lastMessage.sender === 'user') return false;
    // Hide for any message type that expects a button/interactive response
    if (['single-select', 'multi-select', 'feeling-select'].includes(lastMessage.message_type)) {
      return false;
    }
    return lastMessage.message_type === 'text';
  };

  const shouldShowInteractiveElements = (message: Message, index: number): boolean => {
    // Only show interactive elements if this is an assistant message
    if (message.sender !== 'assistant') return false;
    
    // Check if there's a user message after this assistant message
    for (let i = index + 1; i < messages.length; i++) {
      if (messages[i].sender === 'user') {
        return false; // User has already responded, don't show buttons
      }
    }
    
    // This is the latest assistant message with no user response
    return true;
  };

  
  if (loading) return <div className="loading">Loading chat...</div>;

  if (error) {
    return (
      <div className="error">
        <p>Error: {error}</p>
        <button onClick={loadTodaySession}>Retry</button>
      </div>
    );
  }

  return (
    <div className="chat-container">
      <div className="chat-header">
        <div className="chat-title">Chat with Ruby</div>
        <button onClick={handleStartNewConversation} className="new-conversation-button">
          <span className="new-conversation-icon">+</span>
          New Conversation
        </button>
      </div>

      {/* Full-page overlay while connecting (blocks interactions) */}
      {!isConnected && !connectionError && (
        <div className="page-overlay" aria-live="polite" aria-busy="true" role="status">
          <div className="overlay-spinner" />
          <span>Connecting to chat...</span>
        </div>
      )}
      
      {!isConnected && (
        connectionError ? (
          <div className="connection-error-banner">
            <span>⚠️ {connectionError}</span>
            <button onClick={() => window.location.reload()} className="retry-button">Retry</button>
          </div>
        ) : (
          <div className="connection-loading-inline" aria-live="polite">
            <div className="spinner" aria-label="Connecting" />
            <span>Connecting to chat...</span>
          </div>
        )
      )}
      
      <div className="messages-container">
        {messages.map((message, index) => (
          <MessageBubble
            key={`${message.id}-${message.content.length}`}
            message={message}
            onButtonClick={handleButtonClick}
            onMultiSelectSubmit={handleMultiSelectSubmit}
            onFeelingSelect={handleFeelingSelect}
            shouldShowInteractiveElements={shouldShowInteractiveElements(message, index)}
          />
        ))}
        {isThinking && <ThinkingBubble />}
        <div ref={messagesEndRef} />
      </div>
      
      <MessageInput 
        onSendMessage={handleSendMessage}
        disabled={!isConnected || isThinking}
        shouldShow={shouldShowTextInput()}
      />

      {/* Calendar Modal for selecting chemo dates */}
      <CalendarModal
        isOpen={isCalendarModalOpen}
        onClose={() => setIsCalendarModalOpen(false)}
        onDateSelect={handleCalendarDateSelect}
      />
    </div>
  );
};

export default ChatsPage; 