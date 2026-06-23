import React, { useState } from 'react'
import AnswerCard from './components/AnswerCard'
import './App.css'

function App() {
  const [answer, setAnswer] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [query, setQuery] = useState('')

  const handleSearch = async (q) => {
    const searchQuery = q || query
    if (!searchQuery.trim() || loading) return
    setLoading(true)
    setError(null)
    setAnswer(null)
    try {
      const res = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery.trim() })
      })
      if (!res.ok) throw new Error('Request failed')
      const data = await res.json()
      setAnswer(data)
    } catch {
      setError('Failed to get response. Try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleSearch()
    }
  }

  const isFirstVisit = !answer && !loading && !error

  return (
    <div className="app">
      <header className="header">
        <h1 className="brand">NewsVerify</h1>
        <p className="description">Verify news using trusted sources and confidence scoring.</p>
        <p className="tagline">2025–2026 Knowledge Base + Latest News</p>
      </header>

      <div className={`content ${isFirstVisit ? 'content--centered' : ''}`}>
        <div className={`search-section ${isFirstVisit ? 'search-section--hero' : ''}`}>
          <div className="search-row">
            <svg className="search-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
            </svg>
            <input
              className="search-input"
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about any news event..."
              disabled={loading}
            />
            <button className="search-btn" onClick={() => handleSearch()} disabled={loading || !query.trim()}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 12h14M12 5l7 7-7 7"/>
              </svg>
            </button>
          </div>
          {isFirstVisit && (
            <div className="chips">
              <button onClick={() => { setQuery("Champions Trophy 2025 winner"); handleSearch("Champions Trophy 2025 winner") }}>Champions Trophy</button>
              <button onClick={() => { setQuery("Air India Express crash Calicut"); handleSearch("Air India Express crash Calicut") }}>Air India crash</button>
              <button onClick={() => { setQuery("Gaganyaan mission ISRO"); handleSearch("Gaganyaan mission ISRO") }}>Gaganyaan</button>
              <button onClick={() => { setQuery("AI regulation bill 2025"); handleSearch("AI regulation bill 2025") }}>AI regulation</button>
            </div>
          )}
        </div>

        <main className="main">
          {loading && (
            <div className="loader">
              <div className="spinner" />
              <span>Analyzing sources...</span>
            </div>
          )}
          {error && <div className="error-msg">{error}</div>}
          {answer && <AnswerCard data={answer} onNewSearch={handleSearch} />}
        </main>
      </div>
    </div>
  )
}

export default App
