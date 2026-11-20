# Third-party licences

This project is released under the [MIT licence](LICENSE). This file lists every
dependency that ships with it or is used to build it, its licence, and whether it
can be used in a **closed-source commercial product**.

Audit date: 2026-11-20. Versions are the ones installed in the Docker image and
locked in `frontend/package-lock.json`.

**Result: no GPL, LGPL or AGPL component is linked into the application.** Every
dependency is permissive (MIT, BSD, Apache-2.0, ISC, PSF, HPND) except one
runtime package and one build tool under MPL-2.0, explained below.

## Libraries that ship with the app (Python)

| Dependency | Version | Licence | Commercial use | Note |
|---|---|---|---|---|
| fastapi | 0.165.0 | MIT | Yes | Web framework |
| starlette | 1.10.0 | BSD-3-Clause | Yes | Used by FastAPI, also serves the frontend |
| uvicorn | 0.54.0 | BSD-3-Clause | Yes | ASGI server |
| pydantic / pydantic-core | 2.14.4 / 2.50.5 | MIT | Yes | Request and response models |
| httpx | 0.28.1 | BSD-3-Clause | Yes | Calls the Google Drive API |
| python-dotenv | 1.2.4 | BSD-3-Clause | Yes | Reads the local `.env` file |
| pypdf | 7.1.1 | BSD-3-Clause | Yes | Text layer of native PDFs. Chosen instead of PyMuPDF (see "Rejected") |
| pypdfium2 | 5.15.2 | BSD-3-Clause or Apache-2.0 | Yes | Renders scanned PDF pages to images. Bundles the PDFium binary (BSD-3-Clause / Apache-2.0) and its own third-party components, whose licences are listed in the package's licence file |
| pytesseract | 0.3.13 | Apache-2.0 | Yes | Thin wrapper that calls the Tesseract program |
| Pillow | 13.0.0 | MIT-CMU (HPND style) | Yes | Opens and converts images before OCR |

### Transitive Python dependencies

| Dependency | Version | Licence | Commercial use | Note |
|---|---|---|---|---|
| anyio | 4.16.0 | MIT | Yes | |
| click | 8.5.1 | BSD-3-Clause | Yes | |
| h11 | 0.16.0 | MIT | Yes | |
| httpcore | 1.0.9 | BSD-3-Clause | Yes | |
| idna | 3.20 | BSD-3-Clause | Yes | |
| annotated-types | 0.8.0 | MIT | Yes | |
| annotated-doc | 0.0.7 | MIT | Yes | |
| typing-inspection | 0.4.5 | MIT | Yes | |
| typing-extensions | 4.16.0 | PSF-2.0 | Yes | |
| opentelemetry-api | 1.45.2 | Apache-2.0 | Yes | Pulled in by FastAPI |
| packaging | 26.3 | Apache-2.0 or BSD-2-Clause | Yes | |
| **certifi** | 2026.10.23 | **MPL-2.0** | Yes, with a condition | Root certificates used by httpx for HTTPS. MPL-2.0 is a weak, file-level copyleft: it only applies to changes made to certifi's own files. We use it unmodified, so our code stays under MIT and can be closed-source. If certifi were modified, those modified files would have to stay under MPL-2.0 |
| pip | 25.0.1 | MIT | Yes | Present in the base image, not used by the app |

## Libraries that ship with the app (frontend bundle)

| Dependency | Version | Licence | Commercial use | Note |
|---|---|---|---|---|
| react | 19.3.1 | MIT | Yes | |
| react-dom | 19.3.1 | MIT | Yes | |
| scheduler | 0.28.0 | MIT | Yes | Used by React |

No UI library, no CDN and no web font are used: the page uses the system font
stack, so nothing is loaded from Google Fonts or any other third party.

## Build-time tools (not shipped, only the compiled files are)

| Dependency | Version | Licence | Commercial use | Note |
|---|---|---|---|---|
| vite | 8.3.8 | MIT | Yes | |
| @vitejs/plugin-react | 6.3.0 | MIT | Yes | |
| rolldown / @rolldown/pluginutils | 1.2.19 / 1.1.1 | MIT | Yes | Bundler used by Vite |
| @oxc-project/types | 0.156.0 | MIT | Yes | |
| postcss, nanoid, fdir, picomatch, tinyglobby | 8.5.33, 3.3.20, 6.5.0, 4.0.7, 0.2.17 | MIT | Yes | |
| picocolors | 1.1.1 | ISC | Yes | |
| source-map-js | 1.2.3 | BSD-3-Clause | Yes | |
| detect-libc | 2.1.2 | Apache-2.0 | Yes | |
| lightningcss | 1.33.0 | MPL-2.0 | Yes | CSS minifier run during `npm run build`. It is not part of the output and we do not modify it, so MPL-2.0 puts no obligation on our code |

`rolldown` and `lightningcss` install a native binary for the current platform
(`win32-x64-msvc` on the Windows machine used for the audit, a Linux build inside
Docker). Those binaries carry the same licence as their parent package.

## Development tools (not shipped)

| Dependency | Version | Licence | Commercial use | Note |
|---|---|---|---|---|
| pytest | 9.2.0 | MIT | Yes | Tests. Also installs pluggy 1.7.0 (MIT), iniconfig 2.3.1 (MIT), pygments 2.21.0 (BSD-2-Clause) |
| ruff | 0.17.5 | MIT | Yes | Linter |

## System components in the Docker image

| Component | Version | Licence | Commercial use | Note |
|---|---|---|---|---|
| Tesseract OCR | 5.5.0 (Debian 5.5.0-1) | Apache-2.0 | Yes | OCR engine. Keep its licence and copyright notices; Debian installs them in `/usr/share/doc/tesseract-ocr` |
| Leptonica | 1.84.1 | BSD-2-Clause | Yes | Image library used by Tesseract |
| Tesseract language data `eng`, `fra`, `ara` (tessdata_fast) | 4.1.0 (Debian 1:4.1.0-2) | Apache-2.0 | Yes | Trained models, copyright Google Inc. and Hewlett Packard |
| Python | 3.12.16 | PSF-2.0 | Yes | Runtime |
| Debian 13 "trixie" base image (`python:3.12-slim`) | 13 | Mixed, per package | Yes | Contains GPL and LGPL system tools (for example bash and glibc). They run as separate programs in the container: our code does not link to them and does not modify them. If the image is redistributed, the licence texts are in `/usr/share/doc` |
| `node:22-alpine` | 22 | MIT (Node.js) | Yes | Used only in the build stage. Nothing from it is copied into the final image except the compiled static files |

## External service

| Service | Terms | Commercial use | Note |
|---|---|---|---|
| Google Drive API v3 | Google APIs Terms of Service | Yes, within the API quota | Used with a free API key and no user login, to read public folders only. Each user of the app needs their own key. Files are downloaded to a temporary folder, processed and deleted |

## Rejected on licence grounds

| Candidate | Licence | Why it was rejected | Replaced by |
|---|---|---|---|
| PyMuPDF (MuPDF) | AGPL-3.0 | Strong copyleft: using it would force the whole application to be published under the AGPL, or to buy a commercial licence | pypdf (text) and pypdfium2 (rendering) |
| poppler / pdf2image | GPL | Copyleft binary needed at runtime | pypdfium2 |
| Google Fonts or CDN hosted scripts | Various | Adds a third-party request and licence for no benefit in a POC | System font stack, everything bundled locally |

## How this was checked

- Python: `importlib.metadata` run inside the built image (licence field and
  classifiers of every installed package), then confirmed against each project's
  licence file.
- npm: `npx license-checker --csv` in `frontend/` for the whole tree, including
  build tools.
- System packages: the `copyright` files under `/usr/share/doc` in the image.

Re-run these checks when a dependency is added or upgraded.
