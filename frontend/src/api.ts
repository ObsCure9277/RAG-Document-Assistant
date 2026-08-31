const apiToken = import.meta.env.VITE_API_TOKEN ?? "";

export function apiFetch(
  input: RequestInfo | URL,
  init: RequestInit = {},
): Promise<Response> {
  const headers = new Headers(init.headers);
  if (apiToken) headers.set("Authorization", `Bearer ${apiToken}`);
  return fetch(input, { ...init, headers });
}
