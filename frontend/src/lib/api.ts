/**
 * Call the backend health endpoint through the Vite dev proxy.
 *
 * Resolves when the backend reports healthy; throws a clear error otherwise.
 */
export async function checkHealth(signal?: AbortSignal): Promise<void> {
  const response = await fetch('/api/v1/health', { signal })
  if (!response.ok) {
    throw new Error(`Backend health check failed with HTTP ${response.status}`)
  }
}
