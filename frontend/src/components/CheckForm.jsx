function CheckForm({ url, onChange, onSubmit, loading }) {
  return (
    <form className="check-form" onSubmit={onSubmit}>
      <input
        type="url"
        value={url}
        onChange={(e) => onChange(e.target.value)}
        placeholder="https://example.com"
        aria-label="URL to check"
        required
        disabled={loading}
      />
      <button type="submit" disabled={loading || !url.trim()}>
        {loading ? (
          <>
            <span className="spinner" aria-hidden="true" /> Checking…
          </>
        ) : (
          'Check Health'
        )}
      </button>
    </form>
  )
}

export default CheckForm
