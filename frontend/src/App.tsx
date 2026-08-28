import { FormEvent, useEffect, useState } from "react";

type DocumentSummary = { id: string; title: string; original_filename: string; size_bytes: number; status: string };

export function App() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [error, setError] = useState("");
  const load = () => fetch("/api/documents").then((response) => response.json()).then(setDocuments).catch(() => setError("Unable to load documents."));
  useEffect(() => { void load(); }, []);
  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    const input = event.currentTarget.elements.namedItem("file") as HTMLInputElement;
    if (!input.files?.[0]) return;
    const response = await fetch("/api/documents", { method: "POST", body: (() => { const data = new FormData(); data.append("file", input.files![0]); return data; })() });
    if (!response.ok) { const body = await response.json(); setError(body.detail ?? "Upload failed."); return; }
    input.value = ""; await load();
  }
  return <main><h1>Document library</h1><form onSubmit={upload}><input name="file" type="file" accept=".pdf,.docx,.txt,.md,.markdown" /><button>Upload</button></form>{error && <p role="alert">{error}</p>}<ul>{documents.map((document) => <li key={document.id}><strong>{document.title}</strong> — {document.original_filename} ({document.status})</li>)}</ul></main>;
}

