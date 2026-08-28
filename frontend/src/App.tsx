import { FormEvent, useEffect, useState } from "react";
import { Chat } from "./Chat";

type DocumentSummary = { id: string; title: string; original_filename: string; size_bytes: number; status: string; version: number; error_message?: string };

export function App() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [error, setError] = useState("");
  const load = () => fetch("/api/documents").then((response) => response.json()).then(setDocuments).catch(() => setError("Unable to load documents."));
  useEffect(() => { void load(); }, []);

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    const input = event.currentTarget.elements.namedItem("file") as HTMLInputElement;
    if (!input.files?.[0]) return;
    const data = new FormData(); data.append("file", input.files[0]);
    const response = await fetch("/api/documents", { method: "POST", body: data });
    if (!response.ok) { const body = await response.json(); setError(body.detail ?? "Upload failed."); return; }
    input.value = ""; await load();
  }

  async function action(documentId: string, path: string, method: "POST" | "DELETE") {
    const response = await fetch(`/api/documents/${documentId}${path}`, { method });
    if (!response.ok) { const body = await response.json(); setError(body.detail ?? "Request failed."); return; }
    await load();
  }

  return <main><h1>Document library</h1><form onSubmit={upload}><input name="file" type="file" accept=".pdf,.docx,.txt,.md,.markdown" /><button>Upload</button></form>{error && <p role="alert">{error}</p>}<ul>{documents.map((document) => <li key={document.id}><strong>{document.title}</strong> — {document.original_filename} ({document.status}) {document.error_message && <span role="alert">: {document.error_message}</span>} {document.status === "failed" && <button onClick={() => void action(document.id, "/retry", "POST")}>Retry</button>} <button onClick={() => void action(document.id, "/reindex", "POST")}>Re-index</button> <button onClick={() => void action(document.id, "", "DELETE")}>Delete</button></li>)}</ul><Chat /></main>;
}


