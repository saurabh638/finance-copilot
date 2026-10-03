import HealthStatus from './features/health/HealthStatus'

export default function App() {
  return (
    <main className="min-h-screen bg-slate-50 p-6">
      <h1 className="text-2xl font-semibold text-slate-900">Finance Co-pilot</h1>
      <HealthStatus />
    </main>
  )
}
