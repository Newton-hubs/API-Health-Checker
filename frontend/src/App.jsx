import { useEffect, useState } from 'react'
import { checkUrl, getChecks, getStats } from './services/api'
import CheckForm from './components/CheckForm'
import ResultCard from './components/ResultCard'
import StatsPanel from './components/StatsPanel'
import HistoryTable from './components/HistoryTable'
import './App.css'

function App() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [checks, setChecks] = useState([])
  const [stats, setStats] = useState(null)

  async function loadDashboard() {
    try {
      const [checksPage, statsData] = await Promise.all([getChecks(), getStats()])
      setChecks(checksPage.items)
      setStats(statsData)
    } catch (err) {
      setError(err.message)
    }
  }

  // Runs once, after the first render: the empty [] means "no dependencies".
  useEffect(() => {
    loadDashboard()
  }, [])

  async function handleSubmit(event) {
    event.preventDefault()
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      setResult(await checkUrl(url.trim()))
      await loadDashboard()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="app">
      <header>
        <h1>API Health Checker</h1>
        <p className="subtitle">Check whether a URL is up and how fast it responds.</p>
      </header>

      <CheckForm url={url} onChange={setUrl} onSubmit={handleSubmit} loading={loading} />

      {error && (
        <div className="banner banner-error" role="alert">
          {error}
        </div>
      )}

      {result && <ResultCard result={result} />}

      <StatsPanel stats={stats} />
      <HistoryTable checks={checks} />
    </main>
  )
}

export default App
