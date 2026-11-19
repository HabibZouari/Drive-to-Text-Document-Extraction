import { useEffect, useState } from "react";

export default function App() {
  const [apiStatus, setApiStatus] = useState("checking");

  useEffect(() => {
    fetch("/api/health")
      .then((response) => (response.ok ? "online" : "error"))
      .catch(() => "offline")
      .then(setApiStatus);
  }, []);

  return (
    <main className="page">
      <h1>Drive to Text</h1>
      <p className="muted">API status: {apiStatus}</p>
    </main>
  );
}
