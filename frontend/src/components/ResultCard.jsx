function ResultCard({ result }) {
  const up = result.status === 'up'

  return (
    <section className={`card result ${up ? 'result-up' : 'result-down'}`} aria-live="polite">
      <h2>
        <span className={`badge badge-${result.status}`}>{up ? 'UP' : 'DOWN'}</span>{' '}
        <span className="result-url">{result.url}</span>
      </h2>
      <dl className="result-details">
        <div>
          <dt>HTTP status</dt>
          <dd>{result.status_code ?? '—'}</dd>
        </div>
        <div>
          <dt>Response time</dt>
          <dd>{result.response_time_ms != null ? `${result.response_time_ms} ms` : '—'}</dd>
        </div>
      </dl>
      {result.error_message && <p className="result-error">{result.error_message}</p>}
    </section>
  )
}

export default ResultCard
