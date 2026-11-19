const METHOD_LABELS = { pdf_parser: "PDF parser", ocr: "OCR" };

export default function JobProgress({ job }) {
  const { counts } = job;
  const finished = counts.done + counts.failed;

  return (
    <section className="card">
      <div className="table-header">
        <strong>
          {job.status === "completed" ? "Finished" : "Processing"}: {finished} of{" "}
          {counts.total}
        </strong>
        <span className="muted">
          {counts.done} done, {counts.failed} failed
        </span>
      </div>
      <progress value={finished} max={counts.total} />

      <table>
        <thead>
          <tr>
            <th>File</th>
            <th>Status</th>
            <th>Method</th>
            <th className="num">Time</th>
          </tr>
        </thead>
        <tbody>
          {job.files.map((file) => (
            <tr key={file.id}>
              <td className="name">
                {file.name}
                {file.error && <div className="file-error">{file.error}</div>}
              </td>
              <td>
                <span className={`badge ${file.status}`}>{file.status}</span>
              </td>
              <td>{METHOD_LABELS[file.method] ?? "-"}</td>
              <td className="num">
                {file.duration_ms == null ? "-" : `${(file.duration_ms / 1000).toFixed(1)} s`}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
