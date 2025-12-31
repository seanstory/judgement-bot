"use client";

import type { Conversation } from "@/lib/types";

interface ConversationListProps {
  conversations: Conversation[];
  currentConversationId?: string;
  onSelect: (conversationId: string) => void;
  onDelete: (conversationId: string) => void;
  onNew: () => void;
}

export default function ConversationList({
  conversations,
  currentConversationId,
  onSelect,
  onDelete,
  onNew,
}: ConversationListProps) {
  return (
    <div className="w-64 bg-gray-900 border-r border-gray-800 flex flex-col h-screen">
      <div className="p-4 border-b border-gray-800">
        <button
          onClick={onNew}
          className="w-full bg-gold hover:bg-gold-light text-black font-semibold py-2 px-4 rounded-lg transition-colors"
        >
          New Conversation
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {conversations.length === 0 ? (
          <div className="text-gray-500 text-sm text-center mt-4">
            No conversations yet
          </div>
        ) : (
          conversations.map((conversation) => (
            <div
              key={conversation.id}
              className={`group mb-2 p-3 rounded-lg cursor-pointer transition-colors ${
                currentConversationId === conversation.id
                  ? "bg-gray-800 border border-gold"
                  : "bg-gray-800/50 hover:bg-gray-800 border border-transparent"
              }`}
              onClick={() => onSelect(conversation.id)}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-white truncate">
                    {conversation.title || "New Conversation"}
                  </div>
                  <div className="text-xs text-gray-400 mt-1">
                    {new Date(conversation.updatedAt).toLocaleDateString()}
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(conversation.id);
                  }}
                  className="ml-2 text-gray-400 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                  aria-label="Delete conversation"
                >
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                    />
                  </svg>
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="p-4 border-t border-gray-800 text-xs text-gray-500">
        <div className="font-heading font-semibold text-gold mb-1">
          Judgement: Eternal Champions
        </div>
        <div>Rules Assistant</div>
      </div>
    </div>
  );
}
