import '@testing-library/jest-dom/vitest'
import { cleanup, configure } from '@testing-library/react'
import { afterEach } from 'vitest'

// A page test waits on a finder while a whole screen renders and its queries
// resolve. Testing Library's one-second default is tight enough that a busy
// machine fails tests that are not broken: 123 finders here use it, none of them
// with a timeout of their own, and full runs failed twice in thirteen attempts
// on this host — each time a different file, each passing on its own, each taking
// about 1.2 s instead of 20 ms. A real failure still reports the same message,
// five seconds later instead of one.
configure({ asyncUtilTimeout: 5000 })

// Vitest runs without globals, so Testing Library cannot register this itself.
afterEach(() => {
  cleanup()
})
