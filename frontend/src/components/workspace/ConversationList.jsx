import { MessageSquare, Trash2 } from "lucide-react";
import { NavButton } from "../navigation/NavButton.jsx";
import { formatDateTime } from "../../utils/format.js";

export function ConversationList({ conversations, onDeleteConversation, onNavigate, projectId }) {
  if (!conversations.length) {
    return (
      <div className="empty-panel">
        <h3>No conversations yet</h3>
        <p>Start a conversation when you are ready to ask questions about this file.</p>
      </div>
    );
  }

  return (
    <div className="conversation-list">
      {conversations.map((conversation) => (
        <div className="conversation-row" key={conversation.id}>
          <NavButton
            className="conversation-link"
            route="conversation"
            params={{ projectId, conversationId: conversation.id }}
            onNavigate={onNavigate}
          >
            <MessageSquare size={18} />
            <div>
              <strong>{conversation.title}</strong>
              <p>Created {formatDateTime(conversation.created_at)}</p>
            </div>
          </NavButton>
          <button className="icon-text-button" type="button" onClick={() => onDeleteConversation(conversation)}>
            <Trash2 size={16} />
            Delete
          </button>
        </div>
      ))}
    </div>
  );
}
