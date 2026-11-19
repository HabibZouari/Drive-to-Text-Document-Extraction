import { useState } from "react";

import { listFolder } from "../api.js";

export default function FolderForm({ onLoaded }) {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    if (!url.trim()) {
      setError("Paste a public Google Drive folder link first.");
      return;
    }

    setLoading(true);
    setError("");
    try {
      onLoaded(await listFolder(url.trim()));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className="card folder-form" onSubmit={handleSubmit}>
      <label htmlFor="folder-url">Google Drive folder link</label>
      <div className="row">
        <input
          id="folder-url"
          type="text"
          placeholder="https://drive.google.com/drive/folders/..."
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          disabled={loading}
        />
        <button type="submit" disabled={loading}>
          {loading ? "Loading..." : "List files"}
        </button>
      </div>
      <p className="hint">The folder must be shared as "Anyone with the link".</p>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
    </form>
  );
}
