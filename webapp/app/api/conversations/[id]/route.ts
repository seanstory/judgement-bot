import { NextRequest, NextResponse } from "next/server";
import { getConversation, deleteConversation } from "@/lib/kibana-client";
import { getOrCreateSessionId, ownsConversation } from "@/lib/session";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const sessionId = await getOrCreateSessionId();

    // Check ownership
    if (!ownsConversation(id, sessionId)) {
      return NextResponse.json(
        { error: "Conversation not found" },
        { status: 404 }
      );
    }

    const conversation = await getConversation(id);
    return NextResponse.json(conversation);
  } catch (error) {
    console.error("Conversation fetch error:", error);
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? error.message
            : "Failed to fetch conversation",
      },
      { status: 500 }
    );
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const sessionId = await getOrCreateSessionId();

    // Check ownership
    if (!ownsConversation(id, sessionId)) {
      return NextResponse.json(
        { error: "Conversation not found" },
        { status: 404 }
      );
    }

    await deleteConversation(id);
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Conversation delete error:", error);
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? error.message
            : "Failed to delete conversation",
      },
      { status: 500 }
    );
  }
}
