import { NextRequest } from "next/server";
import { sendMessage } from "@/lib/kibana-client";
import { getOrCreateSessionId, trackConversation } from "@/lib/session";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { message, conversationId } = body;

    if (!message || typeof message !== "string") {
      return new Response(
        JSON.stringify({ error: "Message is required" }),
        { status: 400 }
      );
    }

    // Get or create session ID
    const sessionId = await getOrCreateSessionId();

    const stream = await sendMessage(message, conversationId);

    // Extract conversation ID from the stream to track ownership
    // Parse SSE events to extract conversation_id
    let currentEvent = "";
    const transformStream = new TransformStream({
      transform(chunk, controller) {
        const text = new TextDecoder().decode(chunk);

        // Parse SSE events to extract conversation_id
        const lines = text.split('\n');
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            try {
              const eventData = JSON.parse(line.slice(6));
              // Look for conversation_id_set event
              if (currentEvent === 'conversation_id_set') {
                const convId = eventData.data?.conversation_id;
                if (convId) {
                  console.log('Tracking conversation:', convId, 'for session:', sessionId);
                  trackConversation(convId, sessionId);
                }
              }
            } catch (e) {
              // Ignore parse errors
            }
          }
        }

        controller.enqueue(chunk);
      },
    });

    const transformedStream = stream.pipeThrough(transformStream);

    return new Response(transformedStream, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  } catch (error) {
    console.error("Chat API error:", error);
    return new Response(
      JSON.stringify({
        error: error instanceof Error ? error.message : "Failed to send message",
      }),
      { status: 500 }
    );
  }
}
