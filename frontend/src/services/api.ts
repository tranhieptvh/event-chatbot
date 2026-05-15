import type { ChatResponse, SessionData, Event } from '../types';

const API_BASE = '/api';

export const chatAPI = {
  sendMessage: async (sessionId: string | null, message: string): Promise<ChatResponse> => {
    const response = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, message }),
    });
    if (!response.ok) throw new Error('Failed to send message');
    return response.json();
  },

  getSession: async (sessionId: string): Promise<SessionData | null> => {
    const response = await fetch(`${API_BASE}/chat/session/${sessionId}`);
    if (!response.ok) {
      if (response.status === 404) return null;
      throw new Error('Failed to get session');
    }
    return response.json();
  },
};

export const eventsAPI = {
  list: async (): Promise<Event[]> => {
    const response = await fetch(`${API_BASE}/events`);
    if (!response.ok) throw new Error('Failed to fetch events');
    return response.json();
  },
};
