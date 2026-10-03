import { QueryClient } from '@tanstack/react-query'

/** The app's single cache for server state (CODING_STANDARDS section 4.2). */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
})
