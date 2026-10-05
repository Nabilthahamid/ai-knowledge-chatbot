const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export type Citation = {
  document_name: string;
  chunk_index: number;
  text: string;
  page_number: number | null;
  similarity: number;
};

export type ChatSession = {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
};

export type ChatMessage = {
  id: number | string;
  session_id: number;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  created_at: string;
};

export type ChatHistoryResponse = {
  session_id: number;
  messages: ChatMessage[];
};

export type SendMessageResponse = {
  session_id: number;
  user_message: ChatMessage;
  assistant_message: ChatMessage;
  answer: string;
  found_in_knowledge_base: boolean;
  citations: Citation[];
};

export type StreamDonePayload = {
  user_message: ChatMessage;
  assistant_message: ChatMessage;
  answer: string;
  found_in_knowledge_base: boolean;
  citations: Citation[];
};

export type KnowledgeDocument = {
  filename: string;
  original_filename: string;
  extension: string;
  size_bytes: number;
  chunk_count: number;
  modified_at: number;
};

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers);

  if (options?.body) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
    cache: "no-store",
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || "Backend request failed");
  }

  return data;
}

export const chatApi = {
  async createSession(title = "New conversation"): Promise<ChatSession> {
    return request<ChatSession>("/api/v1/chat/sessions", {
      method: "POST",
      body: JSON.stringify({ title }),
    });
  },

  async listSessions(): Promise<{
    sessions: ChatSession[];
  }> {
    return request<{
      sessions: ChatSession[];
    }>("/api/v1/chat/sessions");
  },

  async getMessages(sessionId: number): Promise<ChatHistoryResponse> {
    return request<ChatHistoryResponse>(
      `/api/v1/chat/sessions/${sessionId}/messages`,
    );
  },

  async sendMessage(
    sessionId: number,
    message: string,
    topK = 5,
  ): Promise<SendMessageResponse> {
    return request<SendMessageResponse>(
      `/api/v1/chat/sessions/${sessionId}/messages`,
      {
        method: "POST",
        body: JSON.stringify({
          message,
          top_k: topK,
        }),
      },
    );
  },

  async sendMessageStream(
    sessionId: number,
    message: string,
    topK: number,
    onToken: (text: string) => void,
    onDone: (data: StreamDonePayload) => void,
  ): Promise<void> {
    const response = await fetch(
      `${API_URL}/api/v1/chat/sessions/${sessionId}/messages/stream`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message,
          top_k: topK,
        }),
      },
    );

    if (!response.ok) {
      const data = await response.json();

      throw new Error(data.detail || "Streaming request failed");
    }

    if (!response.body) {
      throw new Error("Streaming is not supported.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();

      if (done) {
        break;
      }

      buffer += decoder.decode(value, {
        stream: true,
      });

      const blocks = buffer.split("\n\n");

      buffer = blocks.pop() || "";

      for (const block of blocks) {
        const eventLine = block
          .split("\n")
          .find((line) => line.startsWith("event:"));

        const dataLine = block
          .split("\n")
          .find((line) => line.startsWith("data:"));

        if (!eventLine || !dataLine) {
          continue;
        }

        const eventName = eventLine.replace("event:", "").trim();

        const jsonText = dataLine.replace("data:", "").trim();

        const data = JSON.parse(jsonText);

        if (eventName === "token") {
          onToken(data.text);
        }

        if (eventName === "done") {
          onDone(data);
        }

        if (eventName === "error") {
          throw new Error(data.message);
        }
      }
    }
  },

  async listDocuments(): Promise<{
    documents: KnowledgeDocument[];
  }> {
    return request<{
      documents: KnowledgeDocument[];
    }>("/api/v1/admin/documents");
  },

  async uploadDocument(file: File) {
    const formData = new FormData();

    formData.append("file", file);

    const response = await fetch(
      `${API_URL}/api/v1/knowledge/documents/upload`,
      {
        method: "POST",
        body: formData,
      },
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Document upload failed");
    }

    return data;
  },

  async deleteDocument(filename: string) {
    return request(`/api/v1/admin/documents/${encodeURIComponent(filename)}`, {
      method: "DELETE",
    });
  },
};
