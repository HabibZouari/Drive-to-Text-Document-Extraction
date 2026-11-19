import { useState } from "react";

import FolderForm from "./components/FolderForm.jsx";

export default function App() {
  const [folder, setFolder] = useState(null);

  return (
    <main className="page">
      <h1>Drive to Text</h1>
      <p className="muted">
        Extract text from the PDFs and images of a public Google Drive folder.
      </p>

      <FolderForm onLoaded={setFolder} />

      {folder && (
        <p className="muted">
          {folder.files.length === 0
            ? "No PDF or image found in this folder."
            : `${folder.files.length} supported file(s) found.`}
        </p>
      )}
    </main>
  );
}
