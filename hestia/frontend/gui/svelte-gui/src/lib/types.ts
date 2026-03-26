export type Role = 'user' | 'assistant' | 'system';
export type ChatMessage = { id: string; role: Role; content: string; createdAt: number };
export type ChatAPIMessages = Omit<ChatMessage, 'id' | 'createdAt'>[];
export type ChatResponse = { response: string };
export type Conversation = { id: string; title: string; createdAt: number; updatedAt?: number; };
