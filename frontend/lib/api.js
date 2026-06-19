function resolveApiBaseUrl() {
  const configuredBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

  if (typeof window === "undefined") {
    return configuredBaseUrl || "http://127.0.0.1:8005";
  }

  const browserHostname = window.location.hostname;
  const browserProtocol = window.location.protocol;

  if (!configuredBaseUrl) {
    return `${browserProtocol}//${browserHostname}:8005`;
  }

  try {
    const configuredUrl = new URL(configuredBaseUrl);
    const configuredHostname = configuredUrl.hostname;
    const isLocalOnlyHost =
      configuredHostname === "localhost" || configuredHostname === "127.0.0.1";
    const browserIsRemoteHost =
      browserHostname !== "localhost" && browserHostname !== "127.0.0.1";

    if (isLocalOnlyHost && browserIsRemoteHost) {
      const port = configuredUrl.port || "8005";
      return `${configuredUrl.protocol}//${browserHostname}:${port}`;
    }

    return configuredBaseUrl;
  } catch {
    return `${browserProtocol}//${browserHostname}:8005`;
  }
}

export async function apiFetch(path, options = {}) {
  const { headers, ...restOptions } = options;
  const apiBaseUrl = resolveApiBaseUrl();
  const response = await fetch(`${apiBaseUrl}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(headers || {})
    },
    ...restOptions
  });

  if (response.status === 204) {
    return null;
  }

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const message = payload?.error || "Something went wrong.";
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return payload;
}
