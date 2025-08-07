const API_BASE = "http://127.0.0.1:8002";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sources?: string[];
  metadata?: string;
  timestamp: string;
}

export interface QueryResponse {
  answer: string;
  sources?: string[];
  metadata_used?: string;
  logs?: string[];
}

export interface UploadResponse {
  message: string;
  files_processed?: number;
}

export interface InspectResponse {
  [key: string]: any;
}

export interface ClearResponse {
  message: string;
  deleted_objects?: number;
}

class ApiService {
  async query(question: string): Promise<QueryResponse> {
    const response = await fetch(`${API_BASE}/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ query: question }),
    });

    if (!response.ok) {
      throw new Error(`Query failed: ${response.statusText}`);
    }

    return response.json();
  }

  async uploadDocuments(files: File[]): Promise<UploadResponse> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append("files", file);
    });

    const response = await fetch(`${API_BASE}/ingest`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`);
    }

    return response.json();
  }

  async inspectStructure(): Promise<InspectResponse> {
    const response = await fetch(`${API_BASE}/inspect`);

    if (!response.ok) {
      throw new Error(`Inspect failed: ${response.statusText}`);
    }

    return response.json();
  }

  async clearIndex(indexName?: string): Promise<ClearResponse> {
    const response = await fetch(`${API_BASE}/clear`, {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ index_name: indexName || null }),
    });

    if (!response.ok) {
      throw new Error(`Clear failed: ${response.statusText}`);
    }

    return response.json();
  }
}

export const apiService = new ApiService();