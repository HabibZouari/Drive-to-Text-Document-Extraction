import { useEffect, useRef } from "react";

import { formatSize } from "../format.js";

export default function FileTable({ files, selected, onToggle, onToggleAll }) {
  const allRef = useRef(null);
  const allSelected = files.length > 0 && selected.size === files.length;
  const someSelected = selected.size > 0 && !allSelected;

  // "indeterminate" can only be set from JavaScript, not through a prop.
  useEffect(() => {
    if (allRef.current) allRef.current.indeterminate = someSelected;
  }, [someSelected]);

  return (
    <section className="card">
      <div className="table-header">
        <label className="select-all">
          <input
            ref={allRef}
            type="checkbox"
            checked={allSelected}
            onChange={onToggleAll}
          />
          Select all
        </label>
        <span className="muted" aria-live="polite">
          {selected.size} of {files.length} selected
        </span>
      </div>

      <table>
        <thead>
          <tr>
            <th aria-label="Select" />
            <th>Name</th>
            <th>Type</th>
            <th className="num">Size</th>
          </tr>
        </thead>
        <tbody>
          {files.map((file) => (
            <tr key={file.id}>
              <td>
                <input
                  type="checkbox"
                  aria-label={`Select ${file.name}`}
                  checked={selected.has(file.id)}
                  onChange={() => onToggle(file.id)}
                />
              </td>
              <td className="name">{file.name}</td>
              <td>{file.type.toUpperCase()}</td>
              <td className="num">{formatSize(file.size)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
