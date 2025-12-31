export interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  updatedAt: string;
}

export interface KibanaMessage {
  role: string;
  content: string;
}

export interface KibanaConversation {
  id: string;
  agent_id: string;
  title: string;
  messages?: KibanaMessage[]; // Only present when fetching specific conversation
  created_at: string;
  updated_at: string;
}

export interface KibanaConverseRequest {
  agent_id: string;
  input: string;
  conversation_id?: string;
}

export interface KibanaConverseResponse {
  conversation_id: string;
  message: string;
}
