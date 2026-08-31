import { FormEvent, useEffect, useRef, useState } from "react";

export type Document = {
  id: string;
  title: string;
  original_filename: string;
  status: "processing" | "indexed" | "failed" | string;
  version: number;
  error_message?: string;
};

export type Citation = {
  document_id: string;
  document_name: string;
  page_number?: number | null;
  excerpt?: string;
};

export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  status?: "complete" | "streaming" | "error" | "insufficient-evidence";
  citations?: Citation[];
  retry?: () => void;
};

type IconName =
  | "upload"
  | "file"
  | "arrow"
  | "alert"
  | "quote"
  | "plus"
  | "trash"
  | "close"
  | "menu";

export function Icon({ name, size = 16 }: { name: IconName; size?: number }) {
  const paths: Record<IconName, string> = {
    upload: "M12 16V4m0 0L7 9m5-5 5 5M5 20h14",
    file: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6",
    arrow: "M12 19V5m0 0L6 11m6-6 6 6",
    alert:
      "M10.3 3.3 2.6 17a2 2 0 0 0 1.7 3h15.4a2 2 0 0 0 1.7-3L13.7 3.3a2 2 0 0 0-3.4 0zM12 9v4m0 4h.01",
    quote:
      "M9 11H5a2 2 0 0 0-2 2v3a2 2 0 0 0 2 2h3a2 2 0 0 0 2-2v-5a5 5 0 0 0-5-5m12 5h-4a2 2 0 0 0-2 2v3a2 2 0 0 0 2 2h3a2 2 0 0 0 2-2v-5a5 5 0 0 0-5-5",
    plus: "M12 5v14M5 12h14",
    trash: "M4 7h16m-10 4v6m4-6v6M9 7V4h6v3m-9 0 1 13h10l1-13",
    close: "M6 6l12 12M18 6 6 18",
    menu: "M4 6h16M4 12h16M4 18h16",
  };
  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={paths[name]} />
    </svg>
  );
}

export function DocumentSidebar({
  documents,
  selectedId,
  onSelect,
  onUpload,
  onDelete,
  deleteError,
  onClose,
}: {
  documents: Document[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onUpload: (files: File[]) => void;
  onDelete: (id: string) => void;
  deleteError?: string;
  onClose: () => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  return (
    <aside className="document-sidebar">
      <div className="sidebar-header">
        <div>
          <p className="overline">Workspace</p>
          <h1>Documents</h1>
        </div>
        <button
          className="icon-button"
          aria-label="Close documents sidebar"
          onClick={onClose}
        >
          <Icon name="close" />
        </button>
      </div>
      <input
        ref={inputRef}
        className="visually-hidden"
        type="file"
        multiple
        accept=".pdf,.docx,.txt,.md,.markdown"
        onChange={(event) => {
          onUpload(Array.from(event.target.files ?? []));
          event.currentTarget.value = "";
        }}
      />
      <button
        className="upload-button"
        onClick={() => inputRef.current?.click()}
      >
        <Icon name="upload" /> Upload
      </button>
      <div className="document-list" aria-label="Uploaded documents">
        {documents.length === 0 ? (
          <p className="sidebar-empty">Your document library is empty.</p>
        ) : (
          documents.map((document) => (
            <div
              className={`document-row ${selectedId === document.id ? "is-selected" : ""}`}
              key={document.id}
            >
              <button
                className="document-select"
                onClick={() => onSelect(document.id)}
              >
                <span className="document-icon">
                  <Icon name="file" size={15} />
                </span>
                <span className="document-row-copy">
                  <strong title={document.original_filename}>
                    {document.original_filename}
                  </strong>
                  <span>
                    {document.status === "processing" ? (
                      <>
                        <i className="status-dot processing" /> Processing
                      </>
                    ) : document.status === "failed" ? (
                      <>
                        <i className="status-dot failed" /> Failed
                      </>
                    ) : (
                      "Ready"
                    )}
                  </span>
                </span>
              </button>
              <button
                className="document-delete"
                aria-label={`Remove ${document.original_filename}`}
                title="Remove document"
                onClick={() => onDelete(document.id)}
              >
                <Icon name="trash" size={14} />
              </button>
            </div>
          ))
        )}
      </div>
      {deleteError && (
        <p className="sidebar-error" role="alert">
          {deleteError}
        </p>
      )}
      <p className="sidebar-foot">
        Click a document to filter the conversation.
      </p>
    </aside>
  );
}

export function CitationChip({
  citation,
  onCitationClick,
}: {
  citation: Citation;
  onCitationClick: (docId: string, page?: number | null) => void;
}) {
  return (
    <button
      className="citation-chip"
      onClick={() =>
        onCitationClick(citation.document_id, citation.page_number)
      }
      title={citation.excerpt}
    >
      <Icon name="quote" size={13} />
      <span>
        {citation.document_name}{" "}
        {citation.page_number
          ? `ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· p. ${citation.page_number}`
          : ""}
      </span>
    </button>
  );
}

export function MessageView({
  message,
  onCitationClick,
}: {
  message: Message;
  onCitationClick: (docId: string, page?: number | null) => void;
}) {
  const insufficient = message.status === "insufficient-evidence";
  return (
    <article
      className={`message message-${message.role} ${insufficient ? "message-insufficient" : ""}`}
    >
      <div className="message-label">
        {message.role === "user" ? "You" : "Assistant"}
      </div>
      {insufficient ? (
        <div className="insufficient-state">
          <Icon name="alert" size={15} />
          <em>
            {message.content ||
              "There is not enough evidence in your documents to answer this."}
          </em>
        </div>
      ) : message.status === "streaming" && !message.content ? (
        <div className="thinking">
          <i />
          <i />
          <i />
        </div>
      ) : (
        <div className="message-text">{message.content}</div>
      )}
      {message.status === "error" && (
        <button className="retry-button" onClick={message.retry}>
          Try again
        </button>
      )}
      {!!message.citations?.length && (
        <div className="citation-list">
          {message.citations.map((citation, index) => (
            <CitationChip
              key={`${citation.document_id}-${citation.page_number}-${index}`}
              citation={citation}
              onCitationClick={onCitationClick}
            />
          ))}
        </div>
      )}
    </article>
  );
}

export function ChatThread({
  messages,
  onCitationClick,
}: {
  messages: Message[];
  onCitationClick: (docId: string, page?: number | null) => void;
}) {
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);
  return (
    <div className="chat-thread" aria-live="polite">
      {messages.length === 0 ? (
        <div className="thread-empty">
          <div className="empty-mark">
            <Icon name="quote" size={20} />
          </div>
          <h2>Ask about your documents</h2>
          <p>Your answers will be grounded in the sources you upload.</p>
        </div>
      ) : (
        messages.map((message) => (
          <MessageView
            key={message.id}
            message={message}
            onCitationClick={onCitationClick}
          />
        ))
      )}
      <div ref={endRef} />
    </div>
  );
}

export function ChatInput({
  onSubmit,
  disabled = false,
}: {
  onSubmit: (message: string) => void;
  disabled?: boolean;
}) {
  const [value, setValue] = useState("");
  function submit(event: FormEvent) {
    event.preventDefault();
    const message = value.trim();
    if (!message || disabled) return;
    onSubmit(message);
    setValue("");
  }
  return (
    <form className="chat-input" onSubmit={submit}>
      <input
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder="Ask about your documents"
        aria-label="Ask about your documents"
      />
      <button
        type="submit"
        aria-label="Send message"
        disabled={!value.trim() || disabled}
      >
        <Icon name="arrow" />
      </button>
    </form>
  );
}
