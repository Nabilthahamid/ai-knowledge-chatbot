"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";

import { chatApi, type KnowledgeDocument } from "@/lib/api";

export default function AdminPage() {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const [loading, setLoading] = useState(false);

  const [message, setMessage] = useState("");

  useEffect(() => {
    void loadDocuments();
  }, []);

  async function loadDocuments() {
    try {
      const result = await chatApi.listDocuments();

      setDocuments(result.documents);
    } catch (error) {
      setMessage(getErrorMessage(error));
    }
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedFile) {
      setMessage("Please select a PDF or TXT file.");

      return;
    }

    try {
      setLoading(true);
      setMessage("");

      await chatApi.uploadDocument(selectedFile);

      setSelectedFile(null);

      setMessage("Document uploaded and indexed successfully.");

      await loadDocuments();
    } catch (error) {
      setMessage(getErrorMessage(error));
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(filename: string) {
    const confirmed = window.confirm(`Delete ${filename}?`);

    if (!confirmed) {
      return;
    }

    try {
      setLoading(true);
      setMessage("");

      await chatApi.deleteDocument(filename);

      setMessage("Document deleted.");

      await loadDocuments();
    } catch (error) {
      setMessage(getErrorMessage(error));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="admin-page">
      <section className="admin-header">
        <div>
          <p className="admin-eyebrow">ADMINISTRATION</p>

          <h1>Knowledge base</h1>

          <p>Upload and manage chatbot documents.</p>
        </div>

        <Link className="back-link" href="/">
          &larr; Back to chat
        </Link>
      </section>

      <section className="admin-card">
        <h2>Upload document</h2>

        <form className="upload-form" onSubmit={handleUpload}>
          <input
            type="file"
            accept=".pdf,.txt"
            onChange={(event) =>
              setSelectedFile(event.target.files?.[0] || null)
            }
          />

          <button type="submit" disabled={loading}>
            {loading ? "Processing..." : "Upload and index"}
          </button>
        </form>

        <p className="admin-note">Supported formats: PDF and TXT.</p>
      </section>

      {message && <div className="admin-message">{message}</div>}

      <section className="admin-card">
        <div className="documents-heading">
          <div>
            <h2>Documents</h2>

            <p>
              {documents.length} document
              {documents.length === 1 ? "" : "s"} indexed
            </p>
          </div>

          <button className="refresh-button" onClick={loadDocuments}>
            Refresh
          </button>
        </div>

        <div className="document-list">
          {documents.length === 0 ? (
            <p className="empty-admin">No documents uploaded yet.</p>
          ) : (
            documents.map((document) => (
              <div className="document-row" key={document.filename}>
                <div className="document-icon">
                  {document.extension.replace(".", "").toUpperCase()}
                </div>

                <div className="document-info">
                  <strong>{document.original_filename}</strong>

                  <span>
                    {formatBytes(document.size_bytes)} &middot; {document.chunk_count}{" "}
                    chunks
                  </span>
                </div>

                <button
                  className="delete-button"
                  onClick={() => handleDelete(document.filename)}
                  disabled={loading}
                >
                  Delete
                </button>
              </div>
            ))
          )}
        </div>
      </section>
    </main>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }

  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }

  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  return "Something went wrong.";
}
