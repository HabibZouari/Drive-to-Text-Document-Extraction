// Thin wrapper around fetch for the FastAPI backend.
// Every failure becomes an Error whose message is safe to show to the user.

async function request(path, options) {
  let response;
  try {
    response = await fetch(path, options);
  } catch {
    throw new Error("Cannot reach the server. Is the backend running?");
  }

  if (!response.ok) {
    let message = `Request failed (${response.status}).`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") {
        message = body.detail;
      } else if (response.status === 422) {
        message = "The request was not valid.";
      }
    } catch {
      // The body was not JSON, keep the generic message.
    }
    throw new Error(message);
  }

  return response.json();
}

export function listFolder(url) {
  return request("/api/folders", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
}

export function getLanguages() {
  return request("/api/languages");
}

export function createJob(folderId, fileIds, language) {
  return request("/api/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ folder_id: folderId, file_ids: fileIds, language }),
  });
}

export function getJob(jobId) {
  return request(`/api/jobs/${jobId}`);
}
