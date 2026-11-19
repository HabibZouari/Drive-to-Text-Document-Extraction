import { useEffect, useState } from "react";

import { createJob, getLanguages } from "./api.js";
import FileTable from "./components/FileTable.jsx";
import FolderForm from "./components/FolderForm.jsx";
import JobProgress from "./components/JobProgress.jsx";
import RunBar from "./components/RunBar.jsx";
import { useJob } from "./useJob.js";

const DEFAULT_LANGUAGES = [{ code: "eng", label: "English" }];

export default function App() {
  const [folder, setFolder] = useState(null);
  const [selected, setSelected] = useState(new Set());
  const [languages, setLanguages] = useState(DEFAULT_LANGUAGES);
  const [language, setLanguage] = useState("eng");
  const [jobId, setJobId] = useState(null);
  const [starting, setStarting] = useState(false);
  const [runError, setRunError] = useState("");
  const { job, error: pollError } = useJob(jobId);

  useEffect(() => {
    getLanguages()
      .then(setLanguages)
      .catch(() => {
        // Keep the default list, English always works.
      });
  }, []);

  const running = starting || (jobId !== null && job?.status !== "completed" && !pollError);

  function handleLoaded(newFolder) {
    setFolder(newFolder);
    setSelected(new Set());
    setJobId(null);
    setRunError("");
  }

  function toggleFile(id) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    setSelected((current) =>
      current.size === folder.files.length
        ? new Set()
        : new Set(folder.files.map((file) => file.id)),
    );
  }

  async function handleRun() {
    setStarting(true);
    setRunError("");
    setJobId(null);
    try {
      const created = await createJob(folder.folder_id, [...selected], language);
      setJobId(created.job_id);
    } catch (err) {
      setRunError(err.message);
    } finally {
      setStarting(false);
    }
  }

  return (
    <main className="page">
      <h1>Drive to Text</h1>
      <p className="muted">
        Extract text from the PDFs and images of a public Google Drive folder.
      </p>

      <FolderForm onLoaded={handleLoaded} />

      {folder &&
        (folder.files.length === 0 ? (
          <p className="muted">No PDF or image found in this folder.</p>
        ) : (
          <>
            <FileTable
              files={folder.files}
              selected={selected}
              onToggle={toggleFile}
              onToggleAll={toggleAll}
            />
            <RunBar
              languages={languages}
              language={language}
              onLanguageChange={setLanguage}
              selectedCount={selected.size}
              running={running}
              onRun={handleRun}
            />
          </>
        ))}

      {(runError || pollError) && (
        <p className="error" role="alert">
          {runError || pollError}
        </p>
      )}
      {job && <JobProgress job={job} />}
    </main>
  );
}
