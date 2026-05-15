import { useState, useEffect, useCallback } from 'react';
import { chatAPI } from '../services/api';
import type { Message } from '../types';

export const useChat = (onEventCreated?: () => void) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);

  useEffect(() => {
    const storedSessionId = sessionStorage.getItem('chatSessionId');
    if (storedSessionId) {
      setSessionId(storedSessionId);
      chatAPI.getSession(storedSessionId)
        .then(data => {
          if (data?.history) setMessages(data.history);
        })
        .catch(err => {
          console.error('Failed to restore session:', err);
          sessionStorage.removeItem('chatSessionId');
          setSessionId(null);
        });
    }
  }, []);

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim()) return;

    const userMessage: Message = { role: 'user', content: text };
    setMessages(prev => [...prev, userMessage]);
    setLoading(true);

    try {
      const response = await chatAPI.sendMessage(sessionId, text);

      if (response.session_id && !sessionId) {
        setSessionId(response.session_id);
        sessionStorage.setItem('chatSessionId', response.session_id);
      }

      const assistantMessage: Message = {
        role: response.role,
        content: response.message,
        scenario: response.scenario,
      };
      setMessages(prev => [...prev, assistantMessage]);
      if (response.scenario === 'success_save') {
        onEventCreated?.();
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: 'Sorry, something went wrong. Please try again.' },
      ]);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  const clearChat = useCallback(() => {
    setMessages([]);
    setSessionId(null);
    sessionStorage.removeItem('chatSessionId');
  }, []);

  return { messages, loading, sessionId, sendMessage, clearChat };
};
