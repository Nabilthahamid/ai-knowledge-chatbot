"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";

import {
  chatApi,
  type ChatMessage,
  type ChatSession,
} from "@/lib/api";

const QUICK_PROMPTS = [
  "Summarize the knowledge base",
  "What are the key topics?",
  "Explain the most important concepts",
];

export default function ChatPage() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [messageInput, setMessageInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [initializing, setInitializing] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    async function loadInitialChat() {
      try {
        const result = await chatApi.listSessions();
        let availableSessions = result.sessions;

        if (availableSessions.length === 0) {
          availableSessions = [await chatApi.createSession()];
        }

        const initialSessionId = availableSessions[0].id;
        const history = await chatApi.getMessages(initialSessionId);

        setSessions(availableSessions);
        setActiveSessionId(initialSessionId);
        setMessages(history.messages);
      } catch (err) {
        setError(getErrorMessage(err));
      } finally {
        setInitializing(false);
      }
    }

    void loadInitialChat();
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function selectSession(sessionId: number) {
    try {
      setError(null);
      setActiveSessionId(sessionId);
      setSidebarOpen(false);
      const history = await chatApi.getMessages(sessionId);
      setMessages(history.messages);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  async function createNewSession() {
    try {
      setError(null);
      const session = await chatApi.createSession();
      setSessions((previous) => [session, ...previous]);
      setActiveSessionId(session.id);
      setMessages([]);
      setSidebarOpen(false);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const message = messageInput.trim();

    if (!message || !activeSessionId || loading) {
      return;
    }

    const sessionId = activeSessionId;
    const timestamp = Date.now();
    const temporaryUserId = `temporary-user-${timestamp}`;
    const temporaryAssistantId = `temporary-assistant-${timestamp}`;
    const currentTime = new Date().toISOString();
    const temporaryUserMessage: ChatMessage = {
      id: temporaryUserId,
      session_id: sessionId,
      role: "user",
      content: message,
      citations: [],
      created_at: currentTime,
    };

    setMessages((previous) => [...previous, temporaryUserMessage]);
    setMessageInput("");
    setLoading(true);
    setError(null);

    let assistantStarted = false;

    try {
      await chatApi.sendMessageStream(
        sessionId,
        message,
        5,
        (token) => {
          setMessages((previous) => {
            if (!assistantStarted) {
              assistantStarted = true;
              return [
                ...previous,
                {
                  id: temporaryAssistantId,
                  session_id: sessionId,
                  role: "assistant",
                  content: token,
                  citations: [],
                  created_at: currentTime,
                },
              ];
            }

            return previous.map((item) =>
              item.id === temporaryAssistantId
                ? { ...item, content: item.content + token }
                : item,
            );
          });
        },
        (data) => {
          setMessages((previous) => {
            const updated = previous.map((item) => {
              if (item.id === temporaryUserId) return data.user_message;
              if (item.id === temporaryAssistantId) return data.assistant_message;
              return item;
            });

            if (!updated.some((item) => item.id === data.assistant_message.id)) {
              updated.push(data.assistant_message);
            }

            return updated;
          });
        },
      );
    } catch (err) {
      setError(getErrorMessage(err));
      setMessages((previous) =>
        previous.filter(
          (item) =>
            item.id !== temporaryUserId && item.id !== temporaryAssistantId,
        ),
      );
    } finally {
      setLoading(false);
    }
  }

  const activeSession = sessions.find((item) => item.id === activeSessionId);

  if (initializing) {
    return (
      <main className="loading-screen">
        <span className="loading-spinner" aria-hidden="true" />
        <span>Loading conversations...</span>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <aside className={`sidebar ${sidebarOpen ? "sidebar-open" : ""}`}>
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">AI</span>
          <div><strong>Knowledge Chat</strong><span>RAG assistant</span></div>
        </div>

        <button className="new-chat-button" onClick={createNewSession}>
          <span aria-hidden="true">+</span> New conversation
        </button>

        <p className="sidebar-label">Conversations</p>
        <div className="session-list">
          {sessions.map((session) => (
            <button
              className={`session-button ${session.id === activeSessionId ? "active" : ""}`}
              key={session.id}
              onClick={() => selectSession(session.id)}
            >
              <span className="session-icon" aria-hidden="true">#</span>
              <span className="session-title">{session.title}</span>
            </button>
          ))}
        </div>

        <div className="sidebar-footer">
          <Link href="/admin">Manage knowledge base</Link>
        </div>
      </aside>

      {sidebarOpen && (
        <button
          className="mobile-overlay"
          aria-label="Close navigation"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <section className="chat-panel">
        <header className="topbar">
          <button
            className="menu-button"
            aria-label="Open navigation"
            onClick={() => setSidebarOpen(true)}
          >
            &#9776;
          </button>
          <div>
            <h1>{activeSession?.title || "New conversation"}</h1>
            <p>Answers are grounded in your uploaded documents.</p>
          </div>
          <div className="topbar-status">
            <span className="status-dot" aria-hidden="true" /> Ready
          </div>
        </header>

        <div className="chat-scroll">
          {messages.length === 0 ? (
            <section className="welcome">
              <div className="welcome-icon" aria-hidden="true">?</div>
              <h2>Ask your knowledge base</h2>
              <p>
                Ask a question and receive an answer grounded in the documents
                uploaded by your team.
              </p>
              <div className="quick-prompts">
                {QUICK_PROMPTS.map((prompt) => (
                  <button key={prompt} onClick={() => setMessageInput(prompt)}>
                    {prompt}<span aria-hidden="true">&rarr;</span>
                  </button>
                ))}
              </div>
            </section>
          ) : (
            messages.map((message) => (
              <article
                className={`message-row ${message.role === "user" ? "user-row" : ""}`}
                key={message.id}
              >
                <div className={`avatar ${message.role === "user" ? "user-avatar" : "assistant-avatar"}`}>
                  {message.role === "user" ? "YOU" : "AI"}
                </div>
                <div className={`message-card ${message.role === "user" ? "user-card" : "assistant-card"}`}>
                  <span className="message-author">
                    {message.role === "user" ? "You" : "Assistant"}
                  </span>
                  <p>{message.content}</p>
                  {message.citations.length > 0 && (
                    <details className="sources">
                      <summary>{message.citations.length} source(s)</summary>
                      <div className="source-list">
                        {message.citations.map((citation, index) => (
                          <span className="source-tag" key={`${citation.document_name}-${citation.chunk_index}-${index}`}>
                            {citation.document_name}
                            {citation.page_number ? `, page ${citation.page_number}` : ""}
                          </span>
                        ))}
                      </div>
                    </details>
                  )}
                </div>
              </article>
            ))
          )}

          {loading && !messages.some((message) => message.id.toString().startsWith("temporary-assistant")) && (
            <div className="message-row">
              <div className="avatar assistant-avatar">AI</div>
              <div className="message-card assistant-card">
                <div className="typing-indicator" aria-label="Assistant is typing">
                  <span /><span /><span />
                </div>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {error && <div className="error-box"><span>!</span>{error}</div>}

        <div className="composer-wrapper">
          <form className="composer" onSubmit={handleSubmit}>
            <textarea
              rows={1}
              value={messageInput}
              placeholder="Ask a question about your documents..."
              onChange={(event) => setMessageInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  event.currentTarget.form?.requestSubmit();
                }
              }}
              disabled={!activeSessionId || loading}
            />
            <button className="send-button" type="submit" disabled={!messageInput.trim() || !activeSessionId || loading} aria-label="Send message">
              &uarr;
            </button>
          </form>
          <p className="composer-hint">Enter to send &middot; Shift+Enter for a new line</p>
        </div>
      </section>
    </main>
  );
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong.";
}
