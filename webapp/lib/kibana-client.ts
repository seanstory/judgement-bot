import type {
  KibanaConversation,
  KibanaConverseRequest,
  KibanaConverseResponse,
} from "./types";

const KIBANA_URL = process.env.KIBANA_URL || "";
const KIBANA_API_KEY = process.env.KIBANA_API_KEY || "";
const KIBANA_AGENT_ID = process.env.KIBANA_AGENT_ID || "";
const KIBANA_SPACE = process.env.KIBANA_SPACE || "default";

const getBaseUrl = () => {
  if (KIBANA_SPACE === "default") {
    return `${KIBANA_URL}/api/agent_builder`;
  }
  return `${KIBANA_URL}/s/${KIBANA_SPACE}/api/agent_builder`;
};

const getHeaders = () => ({
  Authorization: `ApiKey ${KIBANA_API_KEY}`,
  "kbn-xsrf": "true",
  "Content-Type": "application/json",
});

export async function sendMessage(
  message: string,
  conversationId?: string
): Promise<ReadableStream> {
  const url = `${getBaseUrl()}/converse/async`;

  const body: KibanaConverseRequest = {
    agent_id: KIBANA_AGENT_ID,
    input: message,
  };

  if (conversationId) {
    body.conversation_id = conversationId;
  }

  const response = await fetch(url, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Kibana API error: ${response.status} ${response.statusText} - ${errorText}`
    );
  }

  if (!response.body) {
    throw new Error("Response body is null");
  }

  return response.body;
}

export async function getConversations(): Promise<KibanaConversation[]> {
  const url = `${getBaseUrl()}/conversations`;

  const response = await fetch(url, {
    method: "GET",
    headers: getHeaders(),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Kibana API error: ${response.status} ${response.statusText} - ${errorText}`
    );
  }

  const data = await response.json();
  // Response format: {results: [...]}
  return data.results || [];
}

export async function getConversation(
  conversationId: string
): Promise<KibanaConversation> {
  const url = `${getBaseUrl()}/conversations/${conversationId}`;

  const response = await fetch(url, {
    method: "GET",
    headers: getHeaders(),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Kibana API error: ${response.status} ${response.statusText} - ${errorText}`
    );
  }

  return response.json();
}

export async function deleteConversation(
  conversationId: string
): Promise<void> {
  const url = `${getBaseUrl()}/conversations/${conversationId}`;

  const response = await fetch(url, {
    method: "DELETE",
    headers: getHeaders(),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Kibana API error: ${response.status} ${response.statusText} - ${errorText}`
    );
  }
}
