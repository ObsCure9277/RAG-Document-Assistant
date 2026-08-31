import { useEffect, useState } from "react";
import { apiFetch } from "./api";
import {
  ChatInput,
  ChatThread,
  Document,
  DocumentSidebar,
  Icon,
  Message,
} from "./components";

export function RagAssistant() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationId, setConversationId] = useState("");
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(
    null,
  );
  const [uploading, setUploading] = useState(false);
  const [backendOnline, setBackendOnline] = useState(false);
  const [deleteError, setDeleteError] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const loadDocuments = async () => {
    const response = await apiFetch("/api/documents");
    if (response.ok) setDocuments(await response.json());
  };

  useEffect(() => {
    void fetch("/health")
      .then((response) => setBackendOnline(response.ok))
      .catch(() => setBackendOnline(false));
    void loadDocuments();
    void apiFetch("/api/conversations", { method: "POST" }).then(
      async (response) => {
        if (!response.ok) return;
        const conversation = await response.json();
        setConversationId(conversation.id);
      },
    );
  }, []);

  async function removeDocument(documentId: string) {
    const document = documents.find((item) => item.id === documentId);
    if (
      !document ||
      !window.confirm(`Remove "${document.original_filename}" permanently?`)
    )
      return;
    setDeleteError("");
    const response = await apiFetch(`/api/documents/${documentId}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      setDeleteError("Could not remove this document. Please try again.");
      return;
    }
    setDocuments((current) => current.filter((item) => item.id !== documentId));
    if (selectedDocumentId === documentId) setSelectedDocumentId(null);
  }

  async function upload(files: File[]) {
    setUploading(true);
    try {
      for (const file of files) {
        const body = new FormData();
        body.append("file", file);
        await apiFetch("/api/documents", { method: "POST", body });
      }
      await loadDocuments();
    } finally {
      setUploading(false);
    }
  }

  async function submit(message: string) {
    if (!conversationId) return;
    const userId = crypto.randomUUID();
    const assistantId = crypto.randomUUID();
    setMessages((current) => [
      ...current,
      { id: userId, role: "user", content: message, status: "complete" },
      {
        id: assistantId,
        role: "assistant",
        content: "",
        status: "streaming",
        citations: [],
      },
    ]);
    const response = await apiFetch(
      `/api/conversations/${conversationId}/messages`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: message,
          document_ids: selectedDocumentId ? [selectedDocumentId] : undefined,
        }),
      },
    );
    if (!response.ok || !response.body) {
      setMessages((current) =>
        current.map((item) =>
          item.id === assistantId
            ? { ...item, status: "error", retry: () => void submit(message) }
            : item,
        ),
      );
      return;
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let answer = "";
    let citations: Message["citations"] = [];
    let failed = false;
    while (true) {
      const chunk = await reader.read();
      if (chunk.done) break;
      buffer += decoder.decode(chunk.value, { stream: true });
      const frames = buffer.split("\n\n");
      buffer = frames.pop() ?? "";
      for (const frame of frames) {
        const event = frame.match(/^event: (.+)$/m)?.[1];
        const data = frame.match(/^data: (.+)$/m)?.[1];
        if (!data) continue;
        try {
          const parsed = JSON.parse(data);
          if (event === "token") answer += parsed.text ?? "";
          if (event === "citations") citations = parsed;
          if (event === "error") failed = true;
          setMessages((current) =>
            current.map((item) =>
              item.id === assistantId
                ? {
                    ...item,
                    content: answer,
                    citations,
                    status: failed ? "error" : "streaming",
                    retry: failed ? () => void submit(message) : undefined,
                  }
                : item,
            ),
          );
        } catch {
          /* wait for the next complete frame */
        }
      }
    }
    setMessages((current) =>
      current.map((item) =>
        item.id === assistantId
          ? {
              ...item,
              content: answer,
              citations,
              status: failed ? "error" : "complete",
              retry: failed ? () => void submit(message) : undefined,
            }
          : item,
      ),
    );
  }

  function onCitationClick(docId: string) {
    setSelectedDocumentId(docId);
  }

  return (
    <div
      className={`rag-assistant ${sidebarOpen ? "sidebar-open" : "sidebar-closed"}`}
    >
      <DocumentSidebar
        documents={documents}
        selectedId={selectedDocumentId}
        onSelect={setSelectedDocumentId}
        onUpload={upload}
        onDelete={removeDocument}
        deleteError={deleteError}
        onClose={() => setSidebarOpen(false)}
      />
      <main className="chat-panel">
        <header className="chat-header">
          <div className="chat-heading">
            <button
              className="sidebar-toggle"
              aria-label="Open documents sidebar"
              onClick={() => setSidebarOpen(true)}
            >
              <Icon name="menu" size={17} />
            </button>
            <div>
              <p className="overline">Rag assistant</p>
              <h1>Ask your documents</h1>
            </div>
          </div>
          <span className="connection-state">
            <i />{" "}
            {uploading
              ? "Uploading"
              : backendOnline
                ? "Backend connected"
                : "Backend offline"}
          </span>
        </header>
        <ChatThread messages={messages} onCitationClick={onCitationClick} />
        <ChatInput onSubmit={submit} disabled={!conversationId} />
      </main>
    </div>
  );
}

export function App() {
  return <RagAssistant />;
}
