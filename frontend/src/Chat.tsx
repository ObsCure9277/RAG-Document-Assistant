import { FormEvent, useEffect, useState } from "react";

type ChatMessage = {
  id: string;
  role: string;
  content: string;
  status: string;
  citations: Array<{ document_name: string; page_number?: number; excerpt: string }>;
};

export function Chat() {
  const [conversationId, setConversationId] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [content, setContent] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    void fetch("/api/conversations", { method: "POST" })
      .then((response) => response.json())
      .then((conversation) => {
        setConversationId(conversation.id);
        return fetch(`/api/conversations/${conversation.id}/messages`);
      })
      .then((response) => response.json())
      .then(setMessages)
      .catch(() => setError("Unable to start chat."));
  }, []);

  async function send(event: FormEvent) {
    event.preventDefault();
    if (!conversationId || !content.trim()) return;
    const question = content;
    setContent("");
    setError("");
    const response = await fetch(`/api/conversations/${conversationId}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: question }),
    });
    if (!response.ok || !response.body) {
      setError("Unable to send message.");
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let answer = "";
    let eventName = "";
    const assistantId = crypto.randomUUID();
    let assistant: ChatMessage = { id: assistantId, role: "assistant", content: "", status: "streaming", citations: [] };

    setMessages((current) => [...current, { id: crypto.randomUUID(), role: "user", content: question, status: "complete", citations: [] }, assistant]);

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      for (const line of decoder.decode(value).split("\n")) {
        if (line.startsWith("event: ")) { eventName = line.slice(7); continue; }
        if (!line.startsWith("data: ")) continue;
        try {
          const data = JSON.parse(line.slice(6));
          if (eventName === "token") answer += data.text ?? "";
          if (eventName === "citations") assistant = { ...assistant, citations: data };
          if (eventName === "error") {
            assistant = { ...assistant, status: "incomplete" };
            setError(data.detail ?? "The response was interrupted.");
          }
          if (eventName === "complete") assistant = { ...assistant, status: "complete" };
        } catch { /* partial SSE frame */ }
      }
      setMessages((current) => current.map((item) => item.id === assistantId ? { ...assistant, content: answer } : item));
    }
    setMessages((current) => current.map((item) => item.id === assistantId ? { ...assistant, content: answer, status: assistant.status === "streaming" ? "complete" : assistant.status } : item));
  }

  return (
    <section className="chat-panel panel">
      <div className="panel-heading chat-heading">
        <div><p className="eyebrow">Assistant</p><h2>Ask your sources</h2></div>
        <span className="live-badge"><span className="status-dot" />Live</span>
      </div>
      <div className="chat-body">
        {messages.length === 0 ? (
          <div className="chat-empty"><div className="sparkle">✦</div><strong>What would you like to know?</strong><p>Answers are grounded in your indexed documents and include source citations.</p></div>
        ) : messages.map((message) => (
          <article className={`message message-${message.role}`} key={message.id}>
            <span className="message-label">{message.role === "user" ? "You" : "Ragspace"}</span>
            <div className="message-content">{message.content || (message.status === "streaming" ? <span className="typing"><i /><i /><i /></span> : "")}</div>
            {message.citations.length > 0 && <div className="citations">{message.citations.map((citation, index) => <small className="citation" key={index}><span>[{index + 1}]</span>{citation.document_name}{citation.page_number ? `, p. ${citation.page_number}` : ""}<b>{citation.excerpt}</b></small>)}</div>}
          </article>
        ))}
      </div>
      <form className="chat-form" onSubmit={send}>
        <input value={content} onChange={(event) => setContent(event.target.value)} placeholder="Ask anything about your library…" aria-label="Ask about your documents" />
        <button aria-label="Send question" type="submit">↗</button>
      </form>
      {error && <p className="notice chat-notice" role="alert">{error}</p>}
      <p className="chat-footnote">Responses use only evidence found in your documents.</p>
    </section>
  );
}
