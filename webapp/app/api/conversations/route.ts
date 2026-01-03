import { NextResponse } from "next/server";
import { getConversations } from "@/lib/kibana-client";
import { getOrCreateSessionId, getConversationsBySession } from "@/lib/session";

export async function GET() {
  try {
    const sessionId = await getOrCreateSessionId();
    const allConversations = await getConversations();

    // Filter to only conversations owned by this session
    const userConversations = getConversationsBySession(sessionId, allConversations);

    return NextResponse.json(userConversations);
  } catch (error) {
    console.error("Conversations API error:", error);
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? error.message
            : "Failed to fetch conversations",
      },
      { status: 500 }
    );
  }
}
