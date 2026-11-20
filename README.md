# Drive-to-Text

A small web app that reads a public Google Drive folder, lists the PDFs and
images inside, and extracts their text. Native PDFs go through a PDF parser.
Images (and scanned PDFs) go through OCR. You can see the result for each file
and download everything as JSON.

I built it as a proof of concept for the DI Xpertia technical assessment
(TA-2026-01), so it is small on purpose.

## What it does

1. Paste a public Google Drive folder link.
2. The app lists the PDFs and images (PNG, JPG, JPEG) with name, type and size.
3. Tick the files you want, or use "Select all". The number of selected files is always shown.
4. Click "Extract text". The files are processed as one batch and each file shows its own status: pending, processing, done or failed.
5. Open the text of each file, see which method was used (PDF parser or OCR), and export the batch as JSON.

If one file fails (a corrupted PDF for example), the others still finish.

## How it works

```
Browser (React)  <-- polls every second -->  FastAPI  -->  Google Drive API (list + download)
                                                |
                                                +--> batch runner (small thread pool)
                                                        |
                                          .pdf  -->  pypdf (text layer)
                                                        |  no text found? -> render pages -> OCR
                                          .png/.jpg --> Tesseract OCR
```

- The browser never talks to Google. It only talks to my API, so the API key stays on the server.
- Creating a batch returns a job id right away. The browser polls that job to show live progress.
- A scanned PDF has no text layer, so the PDF parser returns almost nothing. When that happens (fewer than 20 characters), the pages are turned into images and sent to OCR, and the result says `ocr`.
- The OCR language (English, French or Arabic) is chosen by the user for the whole batch.

## Technology choices

| Part | Choice | Why |
|---|---|---|
| Backend | Python 3.12, FastAPI | Simple, typed, easy to test, and I know it well |
| Frontend | React + Vite (plain JavaScript) | The page has a lot of state (selection, status per file, polling), and components make that easy to follow. No UI library, to keep it small |
| Drive access | Google Drive API v3 with a free API key | Gives name, type and size, handles pagination, no scraping and no user login. The API is free |
| PDF text | pypdf (BSD-3) | Pure Python and permissive. I did not use PyMuPDF because it is AGPL |
| PDF to image | pypdfium2 | Needed for scanned PDFs, and it avoids poppler (GPL) |
| OCR | Tesseract + pytesseract | Open source, runs locally, has French, English and Arabic |
| Batch | Thread pool + polling | Simple, and gives live progress without websockets |
| Run | Docker Compose | One command. Tesseract and its language packs come inside the image |
| Tests | pytest, ruff | Routing, extraction, batch and API are covered |

Everything is free and open source. The full list with versions and licences
(and what I rejected) is in [LICENSES.md](LICENSES.md).

## Run it with Docker (easiest)

You need Docker and a free Google API key (see below).

```bash
git clone https://github.com/HabibZouari/Drive-to-Text-Document-Extraction.git
cd Drive-to-Text-Document-Extraction
cp .env.example .env        # then open .env and paste your key after GOOGLE_API_KEY=
docker compose up --build
```

Open http://localhost:8000.

If `.env` is missing, `docker compose` stops and says so. If the key is empty,
the page loads but asks for the key when you paste a link.

## Get a free Google API key

1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a project. No billing is needed.
2. Open APIs & Services > Library and enable **Google Drive API**.
3. Open Credentials > Create credentials > **API key**. You can restrict it to the Drive API.
4. Put it in `.env` as `GOOGLE_API_KEY=...`. Never commit this file (it is in `.gitignore`).

The Drive folder must be shared as "Anyone with the link" (viewer).

## Settings

All settings are in `.env`:

| Variable | Default | Meaning |
|---|---|---|
| `GOOGLE_API_KEY` | (empty) | Your Drive API key |
| `MAX_FILE_MB` | 25 | Bigger files are not processed and show a clear error |
| `MAX_FILES_PER_BATCH` | 50 | Maximum files in one batch |
| `BATCH_WORKERS` | 2 | Files processed at the same time (OCR uses a lot of CPU) |

## Run it without Docker

You need Python 3.12, Node 22, and Tesseract with the `fra`, `eng` and `ara`
language packs (on Debian/Ubuntu: `apt install tesseract-ocr tesseract-ocr-fra tesseract-ocr-eng tesseract-ocr-ara`).

```bash
cp .env.example .env                    # add your key
pip install -r requirements.txt
uvicorn app.main:app --reload           # API on http://localhost:8000

cd frontend
npm install
npm run dev                             # UI on http://localhost:5173 (calls the API on :8000)
```

To serve the UI from the API on one port, like in Docker, run `npm run build`
inside `frontend/` and open http://localhost:8000.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
ruff check .
```

The Drive API and the OCR engine are replaced by fakes in the tests, so they run
fast and need no key. One test uses the real Tesseract and is skipped when it is
not installed. There are tests for the folder link parsing, the Drive
client, the routing between parser and OCR, scanned PDF detection, language
selection, the batch runner (including a failing file), and the API endpoints.

## Project structure

```
app/
  main.py            FastAPI app, serves the built frontend
  config.py          settings from environment variables
  schemas.py         request and response models
  api/               routes, error handling, dependencies
  drive/             folder link parsing and Google Drive client
  extraction/        PDF parser, OCR, scanned PDF fallback, routing by file type
  jobs/              batch runner with per-file status
frontend/src/        React app (components, api calls, polling hook)
tests/               pytest tests
Dockerfile, docker-compose.yml
```

## API

| Method and path | What it does |
|---|---|
| `POST /api/folders` | Takes `{ "url": "..." }`, returns the PDFs and images of the folder |
| `GET /api/languages` | OCR languages available |
| `POST /api/jobs` | Takes `{ folder_id, file_ids, language }`, starts a batch, returns a `job_id` |
| `GET /api/jobs/{id}` | Status of the batch and of each file, with the text when done |
| `GET /api/jobs/{id}/export` | Downloads the results as a JSON file |
| `GET /api/health` | Health check |

## Known limits

I want to be clear about what this POC does not do:

- Only the top level of the folder is read. Subfolders are not opened.
- Only PDF, PNG and JPG/JPEG files are listed. Other files are ignored.
- The OCR language applies to images and scanned PDFs, not to native PDFs (they already have their text). It is one language for the whole batch. If you pick Arabic for an English image, the result is wrong. Pick the language that matches your documents.
- A PDF counts as scanned when the parser finds fewer than 20 characters in the whole file. A PDF that mixes real text and scanned pages is treated as a normal PDF, so its scanned pages are not OCRed.
- Scanned PDFs longer than 20 pages are refused, to avoid blocking the server. Files over 25 MB are refused too.
- OCR quality depends on the image. Handwriting and very low resolution scans will not work well.
- Jobs are kept in memory. If the server restarts, the results are lost (export the JSON first). Only the last 50 jobs are kept.
- No login and no user separation. Anyone who can open the page can use the API key behind it, so do not expose it publicly as it is.
- The UI has no automated tests, only the backend does.
- You need your own Google API key, and the Drive API has a daily quota.

## Next steps

- Read subfolders, and handle Google Docs/Sheets exports.
- Choose the OCR language per file, or detect it automatically, and allow mixed languages like Arabic + English.
- Store jobs in a database so they survive a restart, and run the OCR in a real queue (Celery or similar).
- Add rate limiting and a simple login before any public deployment.
- Add UI tests and a CI pipeline that runs tests and linting on each push.
- Better handling of PDFs that mix text and scanned pages (decide page by page).

## Licence

MIT, see [LICENSE](LICENSE). Third-party licences are in [LICENSES.md](LICENSES.md).
