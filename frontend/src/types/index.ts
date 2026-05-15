export type MessageRole = 'user' | 'assistant';

export type Scenario =
  | 'missing_field'
  | 'invalid_input'
  | 'confirmation'
  | 'success_save'
  | 'error_db'
  | 'update_previous_field';

export interface Message {
  role: MessageRole;
  content: string;
  scenario?: Scenario;
}

export interface ChatResponse {
  session_id: string;
  role: MessageRole;
  scenario: Scenario;
  message: string;
}

export interface SessionData {
  history: Message[];
  draft?: Record<string, unknown>;
}

export interface Event {
  id: number;
  name: string;
  date: string;
  time: string;
  description?: string | null;
  seat_types: Record<string, number>;
  purchase_start: string;
  purchase_end: string;
  ticket_limit: number;
  venue_name: string;
  venue_address: string;
  capacity: number;
  organizer_name: string;
  organizer_email: string;
  category?: string | null;
  language?: string | null;
  is_recurring: boolean;
  recurrence_frequency?: string | null;
  is_online: boolean;
  created_at: string;
}
