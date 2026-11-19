import { useState } from "react";

import FileTable from "./components/FileTable.jsx";
import FolderForm from "./components/FolderForm.jsx";

export default function App() {
  const [folder, setFolder] = useState(null);
  const [selected, setSelected] = useState(new Set());

  function handleLoaded(newFolder) {
    setFolder(newFolder);
    setSelected(new Set());
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
          <FileTable
            files={folder.files}
            selected={selected}
            onToggle={toggleFile}
            onToggleAll={toggleAll}
          />
        ))}
    </main>
  );
}
