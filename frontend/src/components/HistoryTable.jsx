function HistoryTable({ checks }) {
  return (
    <section className="card">
      <h2>Recent checks</h2>
      {checks.length === 0 ? (
        <p className="empty">No checks yet. Enter a URL above to run your first one.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>URL</th>
                <th>Status</th>
                <th>HTTP</th>
                <th>Time</th>
                <th>Checked at</th>
              </tr>
            </thead>
            <tbody>
              {checks.map((check) => (
                <tr key={check.id}>
                  <td className="cell-url" title={check.url}>
                    {check.url}
                  </td>
                  <td>
                    <span className={`badge badge-${check.status}`}>{check.status.toUpperCase()}</span>
                  </td>
                  <td>{check.status_code ?? '—'}</td>
                  <td>{check.response_time_ms != null ? `${check.response_time_ms} ms` : '—'}</td>
                  <td>{new Date(check.checked_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

export default HistoryTable
