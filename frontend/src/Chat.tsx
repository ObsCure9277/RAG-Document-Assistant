import { FormEvent, useEffect, useState } from "react";

type ChatMessage = { id: string; role: string; content: string; status: string; citations: Array<{ document_name: string; page_number?: number; excerpt: string }> };

export function Chat() {
  const [conversationId, setConversationId] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [content, setContent] = useState("");
  const [error, setError] = useState("");
  useEffect(() => { void fetch("/api/conversations", { method: "POST" }).then((response) => response.json()).then((conversation) => { setConversationId(conversation.id); return fetch(`/api/conversations/${conversation.id}/messages`); }).then((response) => response.json()).then(setMessages).catch(() => setError("Unable to start chat.")); }, []);

  async function send(event: FormEvent) {
    event.preventDefault();
    if (!conversationId || !content.trim()) return;
    const question = content; setContent(""); setError("");
    const response = await fetch(`/api/conversations/${conversationId}/messages`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content: question }) });
    if (!response.ok || !response.body) { setError("Unable to send message."); return; }
    const reader = response.body.getReader(); const decoder = new TextDecoder(); let answer = ""; let eventName = ""; const assistantId = crypto.randomUUID(); let assistant: ChatMessage = { id: assistantId, role: "assistant", content: "", status: "streaming", citations: [] };
    setMessages((current) => [...current, { id: crypto.randomUUID(), role: "user", content: question, status: "complete", citations: [] }, assistant]);
    while (true) {
      const { value, done } = await reader.read(); if (done) break;
      for (const line of decoder.decode(value).split("\n")) {
        if (line.startsWith("event: ")) { eventName = line.slice(7); continue; }
        if (!line.startsWith("data: ")) continue;
        try { const data = JSON.parse(line.slice(6)); if (eventName === "token") answer += data.text ?? ""; if (eventName === "citations") assistant = { ...assistant, citations: data }; if (eventName === "error") { assistant = { ...assistant, status: "incomplete" }; setError(data.detail ?? "The response was interrupted."); } } catch { /* wait for the next event */ }
      }
      setMessages((current) => current.map((item) => item.id === assistantId ? { ...assistant, content: answer } : item));
    }
  }

  return <section><h2>Chat</h2><div>{messages.map((message) => <article key={message.id}><strong>{message.role}:</strong> {message.content} {message.citations.map((citation, index) => <small key={index}> [{citation.document_name}{citation.page_number ? `, p. ${citation.page_number}` : ""}: {citation.excerpt}]</small>)}</article>)}</div><form onSubmit={send}><input value={content} onChange={(event) => setContent(event.target.value)} placeholder="Ask about your documents" /><button>Send</button></form>{error && <p role="alert">{error}</p>}</section>;
}
