import { FormEvent, useEffect, useState } from "react";
import { Chat } from "./Chat";

type DocumentSummary = {
  id: string;
  title: string;
  original_filename: string;
  size_bytes: number;
  status: string;
  version: number;
  error_message?: string;
};

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
function Status({ value }: { value: string }) {
  const label =
    value === "indexed" ? "Ready" : value === "processing" ? "Indexing" : value;
  return (
    <span className={`status status-${value}`}>
      <span className="status-dot" />
      {label}
    </span>
  );
}

export function App() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<string[]>([]);
  const load = () =>
    fetch("/api/documents")
      .then((response) => response.json())
      .then(setDocuments)
      .catch(() => setError("Unable to load documents."));
  useEffect(() => {
    void load();
    const interval = window.setInterval(() => void load(), 1500);
    return () => window.clearInterval(interval);
  }, []);

  async function uploadFiles(files: File[]) {
    if (!files.length) return;
    setError("");
    setUploading(true);
    const failures: string[] = [];
    try {
      for (const file of files) {
        const data = new FormData();
        data.append("file", file);
        const response = await fetch("/api/documents", { method: "POST", body: data });
        if (!response.ok) {
          const body = await response.json().catch(() => ({}));
          failures.push(file.name + ": " + (body.detail ?? "upload failed"));
        }
      }
      await load();
      if (failures.length) setError(failures.join(" · "));
    } catch {
      setError("Upload failed. Check that the API is running.");
    } finally {
      setUploading(false);
    }
  }

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const input = event.currentTarget.elements.namedItem("file") as HTMLInputElement;
    await uploadFiles(Array.from(input.files ?? []));
    input.value = "";
    setSelectedFiles([]);
  }

  function selectFiles(event: React.ChangeEvent<HTMLInputElement>) {
    setSelectedFiles(Array.from(event.target.files ?? []).map((file) => file.name));
  }

  async function action(
    documentId: string,
    path: string,
    method: "POST" | "DELETE",
  ) {
    setError("");
    const response = await fetch(`/api/documents/${documentId}${path}`, {
      method,
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      setError(body.detail ?? "Request failed.");
      return;
    }
    await load();
  }

  const indexed = documents.filter(
    (document) => document.status === "indexed",
  ).length;
  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/">
          <span className="brand-mark">R</span>
          <span>ragspace</span>
        </a>
        <div className="topbar-meta">
          <span className="pulse" />
          Personal knowledge base
        </div>
      </header>
      <main className="page">
        <section className="hero">
          <div>
            <p className="eyebrow">Workspace</p>
            <h1>
              Your documents,
              <br />
              <em>ready to think with.</em>
            </h1>
            <p className="hero-copy">
              Upload reference material and ask questions grounded in the
              source.
            </p>
          </div>
          <div className="hero-stats">
            <div>
              <strong>{documents.length}</strong>
              <span>Documents</span>
            </div>
            <div>
              <strong>{indexed}</strong>
              <span>Searchable</span>
            </div>
          </div>
        </section>
        <section className="workspace-grid">
          <div className="library-panel panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Library</p>
                <h2>Source material</h2>
              </div>
              <span className="count-badge">{documents.length}</span>
            </div>
            <form className="upload-zone" onSubmit={upload}>
              <input
                id="file-upload"
                name="file"
                type="file"
                multiple
                accept=".pdf,.docx,.txt,.md,.markdown"
                onChange={selectFiles}
              />
              <label htmlFor="file-upload" className="upload-label">
                <span className="upload-icon">↑</span>
                <span>
                  <strong>{uploading ? "Uploading…" : selectedFiles.length ? selectedFiles.length + " file(s) selected" : "Add documents"}</strong>
                  <small>PDF, DOCX, TXT or Markdown · multiple files</small>
                </span>
                <span className="browse">Browse</span>
              </label>
              <button
                className="upload-submit"
                type="submit"
                disabled={uploading || selectedFiles.length === 0}
              >
                Upload
              </button>
            </form>
            {error && (
              <p className="notice" role="alert">
                {error}
              </p>
            )}
            {!documents.length ? (
              <div className="empty-state">
                <span className="empty-icon">✦</span>
                <strong>Your library is empty</strong>
                <p>
                  Add documents to give your assistant something to work with.
                </p>
              </div>
            ) : (
              <ul className="document-list">
                {documents.map((document) => (
                  <li className="document-card" key={document.id}>
                    <span className="file-icon">↗</span>
                    <div className="document-info">
                      <strong title={document.title}>{document.title}</strong>
                      <span>
                        {document.original_filename} ·{" "}
                        {formatSize(document.size_bytes)} · v{document.version}
                      </span>
                      {document.error_message && (
                        <small className="document-error" role="alert">
                          {document.error_message}
                        </small>
                      )}
                    </div>
                    <div className="document-actions">
                      <Status value={document.status} />
                      <div className="action-row">
                        {document.status === "failed" && (
                          <button
                            onClick={() =>
                              void action(document.id, "/retry", "POST")
                            }
                          >
                            Retry
                          </button>
                        )}
                        <button
                          onClick={() =>
                            void action(document.id, "/reindex", "POST")
                          }
                        >
                          Re-index
                        </button>
                        <button
                          className="danger"
                          onClick={() => void action(document.id, "", "DELETE")}
                        >
                          Remove
                        </button>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <Chat />
        </section>
      </main>
      <footer>
        <span>Private by default</span>
        <span>•</span>
        <span>Evidence-first answers</span>
      </footer>
    </div>
  );
}
