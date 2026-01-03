import { cookies } from "next/headers";
import { randomBytes } from "crypto";

const SESSION_COOKIE_NAME = "judgement_session_id";
const COOKIE_MAX_AGE = 60 * 60 * 24 * 365; // 1 year

// In-memory store for conversation ownership
// Key: conversation_id, Value: session_id
const conversationOwnership = new Map<string, string>();

export async function getOrCreateSessionId(): Promise<string> {
  const cookieStore = await cookies();
  const existingSessionId = cookieStore.get(SESSION_COOKIE_NAME)?.value;

  if (existingSessionId) {
    return existingSessionId;
  }

  // Generate new session ID
  const newSessionId = randomBytes(32).toString("hex");
  cookieStore.set(SESSION_COOKIE_NAME, newSessionId, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: COOKIE_MAX_AGE,
    path: "/",
  });

  return newSessionId;
}

export function trackConversation(conversationId: string, sessionId: string) {
  conversationOwnership.set(conversationId, sessionId);
  console.log(`[Session] Tracked conversation ${conversationId} for session ${sessionId.slice(0, 8)}...`);
  console.log(`[Session] Total tracked conversations: ${conversationOwnership.size}`);
}

export function getConversationsBySession(
  sessionId: string,
  allConversations: Array<{ id: string }>
): Array<{ id: string }> {
  console.log(`[Session] Filtering ${allConversations.length} conversations for session ${sessionId.slice(0, 8)}...`);
  console.log(`[Session] Tracked conversations:`, Array.from(conversationOwnership.entries()));

  const filtered = allConversations.filter(
    (conv) => conversationOwnership.get(conv.id) === sessionId
  );

  console.log(`[Session] Returning ${filtered.length} conversations for this session`);
  return filtered;
}

export function ownsConversation(
  conversationId: string,
  sessionId: string
): boolean {
  return conversationOwnership.get(conversationId) === sessionId;
}
