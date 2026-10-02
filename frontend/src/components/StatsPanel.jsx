function StatsPanel({ stats }) {
  const tiles = [
    { label: 'Total checks', value: stats?.total_checks },
    { label: 'Successful', value: stats?.successful_checks },
    { label: 'Failed', value: stats?.failed_checks },
    {
      label: 'Avg response',
      value: stats?.average_response_time_ms != null ? `${stats.average_response_time_ms} ms` : null,
    },
  ]

  return (
    <section className="stats" aria-label="Statistics">
      {tiles.map((tile) => (
        <div className="card stat" key={tile.label}>
          <span className="stat-value">{tile.value ?? '—'}</span>
          <span className="stat-label">{tile.label}</span>
        </div>
      ))}
    </section>
  )
}

export default StatsPanel
