"use client";

import { useState, useEffect, useRef } from "react";
import ChatMessage from "@/components/ChatMessage";
import ChatInput from "@/components/ChatInput";
import ConversationList from "@/components/ConversationList";
import type { Message, Conversation, KibanaConversation } from "@/lib/types";

export default function Home() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<
    string | undefined
  >();
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = async () => {
    try {
      const response = await fetch("/api/conversations");
      if (!response.ok) {
        // Don't show error for 404 or empty conversations
        if (response.status === 404) {
          setConversations([]);
          return;
        }
        throw new Error("Failed to load conversations");
      }

      const kibanaConversations: KibanaConversation[] = await response.json();
      const formattedConversations: Conversation[] = kibanaConversations
        .map((conv) => ({
          id: conv.id,
          title: conv.title || "New Conversation",
          messages: [], // Messages not included in list endpoint
          updatedAt: conv.updated_at || conv.created_at,
        }))
        .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()); // Most recent first

      setConversations(formattedConversations);
    } catch (err) {
      console.error("Failed to load conversations:", err);
      // Don't set error state - conversations are optional
      setConversations([]);
    }
  };

  const loadConversation = async (conversationId: string) => {
    try {
      const response = await fetch(`/api/conversations/${conversationId}`);
      if (!response.ok) throw new Error("Failed to load conversation");

      const data: any = await response.json();

      // Parse rounds structure to extract messages
      const formattedMessages: Message[] = [];
      if (data.rounds && Array.isArray(data.rounds)) {
        for (const round of data.rounds) {
          // Add user message
          if (round.input?.message) {
            formattedMessages.push({
              role: "user",
              content: round.input.message,
              timestamp: data.updated_at || data.created_at,
            });
          }

          // Add assistant response
          if (round.response?.message) {
            formattedMessages.push({
              role: "assistant",
              content: round.response.message,
              timestamp: data.updated_at || data.created_at,
            });
          }
        }
      }

      setMessages(formattedMessages);
      setCurrentConversationId(conversationId);
      setError(null);
    } catch (err) {
      console.error("Failed to load conversation:", err);
      setError("Failed to load conversation");
    }
  };

  const handleSendMessage = async (content: string) => {
    const userMessage: Message = {
      role: "user",
      content,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: content,
          conversationId: currentConversationId,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        let errorData;
        try {
          errorData = JSON.parse(errorText);
        } catch {
          throw new Error(`Failed to send message: ${response.statusText}`);
        }
        throw new Error(errorData.error || "Failed to send message");
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error("No response body");
      }

      let assistantContent = "";
      let newConversationId: string | undefined;
      let currentReasoning = "";
      let buffer = "";
      let currentEvent = "";
      let isStreaming = false; // Track if we're streaming the actual response

      // Add a temporary assistant message that we'll update
      const tempMessageIndex = messages.length + 1;
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Thinking...",
          timestamp: new Date().toISOString(),
        },
      ]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;

        // Process complete lines only
        const lines = buffer.split("\n");
        buffer = lines.pop() || ""; // Keep the last incomplete line in buffer

        for (const line of lines) {
          if (!line.trim()) continue;

          // SSE format: "event: <event_name>" followed by "data: <json>"
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            const jsonStr = line.slice(6);
            try {
              const eventData = JSON.parse(jsonStr);

              if (currentEvent === "conversation_id_set") {
                newConversationId = eventData.data?.conversation_id;
              } else if (currentEvent === "reasoning" && !isStreaming) {
                const reasoningText = eventData.data?.reasoning;
                if (reasoningText) {
                  currentReasoning = reasoningText;
                  // Update message with current reasoning
                  setMessages((prev) => {
                    const updated = [...prev];
                    updated[tempMessageIndex] = {
                      ...updated[tempMessageIndex],
                      content: `${currentReasoning}...`,
                    };
                    return updated;
                  });
                }
              } else if (currentEvent === "tool_call" && !isStreaming) {
                const toolId = eventData.data?.tool_id;
                const params = eventData.data?.params;
                if (toolId) {
                  const toolDesc = params
                    ? `Calling ${toolId} with: ${JSON.stringify(params)}`
                    : `Calling ${toolId}`;
                  // Update message with tool call info
                  setMessages((prev) => {
                    const updated = [...prev];
                    updated[tempMessageIndex] = {
                      ...updated[tempMessageIndex],
                      content: `🔧 ${toolDesc}...`,
                    };
                    return updated;
                  });
                }
              } else if (currentEvent === "tool_progress" && !isStreaming) {
                const progressMsg = eventData.data?.message;
                if (progressMsg) {
                  // Update message with progress
                  setMessages((prev) => {
                    const updated = [...prev];
                    updated[tempMessageIndex] = {
                      ...updated[tempMessageIndex],
                      content: `${progressMsg}...`,
                    };
                    return updated;
                  });
                }
              } else if (currentEvent === "message_chunk") {
                // Stream the actual response chunks
                isStreaming = true;
                const textChunk = eventData.data?.text_chunk;
                if (textChunk) {
                  assistantContent += textChunk;
                  // Update with accumulated content
                  setMessages((prev) => {
                    const updated = [...prev];
                    updated[tempMessageIndex] = {
                      ...updated[tempMessageIndex],
                      content: assistantContent,
                    };
                    return updated;
                  });
                }
              } else if (currentEvent === "message_complete") {
                // Final message already accumulated
                isStreaming = false;
              }
            } catch (e) {
              console.error("Failed to parse SSE event:", jsonStr, e);
            }
          }
        }
      }

      if (!currentConversationId && newConversationId) {
        setCurrentConversationId(newConversationId);
        await loadConversations();
      }
    } catch (err) {
      console.error("Failed to send message:", err);
      setError(
        err instanceof Error ? err.message : "Failed to send message"
      );
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewConversation = () => {
    setCurrentConversationId(undefined);
    setMessages([]);
    setError(null);
    setIsLoading(false);
  };

  const handleDeleteConversation = async (conversationId: string) => {
    try {
      const response = await fetch(`/api/conversations/${conversationId}`, {
        method: "DELETE",
      });

      if (!response.ok) throw new Error("Failed to delete conversation");

      if (currentConversationId === conversationId) {
        handleNewConversation();
      }

      await loadConversations();
    } catch (err) {
      console.error("Failed to delete conversation:", err);
      setError("Failed to delete conversation");
    }
  };

  return (
    <div className="flex h-screen">
      <ConversationList
        conversations={conversations}
        currentConversationId={currentConversationId}
        onSelect={loadConversation}
        onDelete={handleDeleteConversation}
        onNew={handleNewConversation}
      />

      <div className="flex-1 flex flex-col">
        <header className="bg-gray-900 border-b border-gray-800 px-6 py-4">
          <h1 className="font-heading text-2xl font-semibold text-gold">
            Judgement Rules Assistant
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            AI-powered rules search for Judgement: Eternal Champions
          </p>
        </header>

        <div className="flex-1 overflow-y-auto p-6">
          {messages.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center text-gray-400 max-w-md">
                <div className="font-heading text-4xl text-gold mb-4">
                  Welcome
                </div>
                <p className="text-lg mb-6">
                  Ask me anything about the rules of Judgement: Eternal
                  Champions
                </p>
                <div className="text-sm text-gray-500">
                  <p className="mb-2">Example questions:</p>
                  <ul className="space-y-1">
                    <li>&quot;How does charging work?&quot;</li>
                    <li>&quot;What are the phases of a turn?&quot;</li>
                    <li>&quot;Explain line of sight rules&quot;</li>
                  </ul>
                </div>
              </div>
            </div>
          ) : (
            <>
              {messages.map((message, index) => (
                <ChatMessage key={index} message={message} />
              ))}
              {isLoading && (
                <div className="flex justify-start mb-4">
                  <div className="bg-gray-800 text-white border border-gray-700 rounded-lg px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-gold rounded-full animate-bounce" />
                      <div
                        className="w-2 h-2 bg-gold rounded-full animate-bounce"
                        style={{ animationDelay: "0.2s" }}
                      />
                      <div
                        className="w-2 h-2 bg-gold rounded-full animate-bounce"
                        style={{ animationDelay: "0.4s" }}
                      />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {error && (
          <div className="mx-6 mb-4 bg-red-900/20 border border-red-500/50 text-red-400 px-4 py-3 rounded-lg">
            {error}
          </div>
        )}

        <div className="border-t border-gray-800 p-6">
          <ChatInput onSend={handleSendMessage} disabled={isLoading} />
        </div>
      </div>
    </div>
  );
}
