import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { fetchSession, login, logout } from '../../lib/api'

export const sessionQueryKey = ['session'] as const

interface Credentials {
  email: string
  password: string
}

/** The current session, or null when logged out. */
export function useSession() {
  return useQuery({ queryKey: sessionQueryKey, queryFn: fetchSession })
}

/** Log in and put the user straight into the session cache. */
export function useLogin() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ email, password }: Credentials) => login(email, password),
    onSuccess: (user) => {
      queryClient.setQueryData(sessionQueryKey, user)
    },
  })
}

/** Log out and clear the session cache. */
export function useLogout() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: logout,
    onSuccess: () => {
      queryClient.setQueryData(sessionQueryKey, null)
    },
  })
}
