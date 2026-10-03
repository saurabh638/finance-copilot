import { useEffect, useState } from 'react'

import { checkHealth } from '../../lib/api'

type HealthState = 'checking' | 'ok' | 'error'

export default function HealthStatus() {
  const [state, setState] = useState<HealthState>('checking')
  const [errorMessage, setErrorMessage] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    let active = true

    checkHealth(controller.signal)
      .then(() => {
        if (active) {
          setState('ok')
        }
      })
      .catch((error: unknown) => {
        if (!active) {
          return
        }
        setState('error')
        setErrorMessage(error instanceof Error ? error.message : 'Unknown error')
      })

    return () => {
      active = false
      controller.abort()
    }
  }, [])

  if (state === 'checking') {
    return <p className="text-slate-600">Checking backend…</p>
  }

  if (state === 'ok') {
    return <p className="text-green-700">Backend OK</p>
  }

  return (
    <p role="alert" className="text-red-700">
      Backend unavailable: {errorMessage}
    </p>
  )
}
