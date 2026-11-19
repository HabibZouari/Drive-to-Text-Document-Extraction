const METHOD_LABELS = { pdf_parser: "PDF parser", ocr: "OCR" };

export default function JobProgress({ job }) {
  const { counts } = job;
  const finished = counts.done + counts.failed;
  const completed = job.status === "completed";

  return (
    <section className="card">
      <div className="table-header">
        <strong>
          {completed ? "Finished" : "Processing"}: {finished} of {counts.total}
        </strong>
        <span className="muted">
          {counts.done} done, {counts.failed} failed
        </span>
        {completed ? (
          <a className="button" href={`/api/jobs/${job.job_id}/export`} download>
            Export JSON
          </a>
        ) : (
          <span className="button disabled" aria-disabled="true">
            Export JSON
          </span>
        )}
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
                {file.status === "done" && (
                  <details>
                    <summary>Show extracted text</summary>
                    {file.text ? (
                      <pre dir="auto">{file.text}</pre>
                    ) : (
                      <p className="muted">No text was found in this file.</p>
                    )}
                  </details>
                )}
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
