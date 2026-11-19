export default function RunBar({
  languages,
  language,
  onLanguageChange,
  selectedCount,
  running,
  onRun,
}) {
  return (
    <section className="card run-bar">
      <label className="field">
        OCR language
        <select
          value={language}
          onChange={(event) => onLanguageChange(event.target.value)}
          disabled={running}
        >
          {languages.map((item) => (
            <option key={item.code} value={item.code}>
              {item.label}
            </option>
          ))}
        </select>
      </label>
      <button type="button" onClick={onRun} disabled={running || selectedCount === 0}>
        {running ? "Processing..." : `Extract text (${selectedCount})`}
      </button>
    </section>
  );
}
