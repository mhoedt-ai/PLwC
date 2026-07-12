# PLwC Document Worker MVP

This directory defines the prepared Docker worker image for future governed
document operations.

Image name:

```text
plwc-document-worker:0.1.0
```

The worker is separate from the `plwc-gateway` runtime. It is not a public MCP
server and must be invoked only through PLwC-controlled policy and audit code.

## Runtime Rules

- The gateway must run the worker with `--pull never`.
- The gateway must run the worker with `--network none`.
- The worker must mount the user workspace at `/work`.
- The worker must not assume `/workspace`.
- The worker must not run `pip install` at runtime.
- The worker image must already be available locally.
- Generated artifacts must remain under `/work`.

## Offline Wheelhouse Build Strategy

Release-quality builds require a verified offline wheelhouse:

```powershell
python scripts\build_document_worker_wheelhouse.py --clean --download
```

This script downloads Linux CPython 3.12 compatible wheels where available,
builds a pure-Python wheel for `odfpy==1.4.1`, writes
`requirements-doc-worker.lock`, and writes `wheelhouse-manifest.json` /
`wheelhouse-manifest.csv`.

The wheel files are local build artifacts under `docker/document-worker/wheelhouse/`
and are intentionally ignored by Git.

After the wheelhouse is present:

```powershell
docker build -t plwc-document-worker:0.1.0 docker/document-worker
```

Current build evidence:

```text
image: plwc-document-worker:0.1.0
digest: sha256:ba166e0bdcd8cfe0b854505990c171afd8068cdd88fa06343f3183bf21c733da
size: 189903296 bytes
```

Build-time internet was used for wheelhouse preparation and Debian native
runtime libraries required by WeasyPrint. Runtime execution remains offline and
uses `--pull never` plus `--network none`.

## MVP Commands

Inside the worker image:

```text
python -m plwc_document_worker probe
python -m plwc_document_worker create-docx --output /work/example.docx
python -m plwc_document_worker create-xlsx --output /work/example.xlsx
python -m plwc_document_worker create-pptx --output /work/example.pptx
python -m plwc_document_worker create-pdf --output /work/example.pdf
python -m plwc_document_worker inspect-zip --input /work/example.zip
python -m plwc_document_worker extract-zip --input /work/example.zip --output-dir /work/extracted
python -m plwc_document_worker create-zip --inputs-json "[\"/work/project\"]" --output /work/project.zip
```

These commands are worker-level smoke commands. Public access remains only
through `plwc_document_operation`; the worker is not a public MCP server.
Conversion, LibreOffice, Pandoc, non-ZIP archive formats, encrypted/password
ZIPs, nested archive extraction and delete are not implemented in this MVP.

## Verification

```powershell
docker run --rm --pull never --network none plwc-document-worker:0.1.0 probe
python -m pytest tests\integration\test_document_worker_mvp.py -q -rs
```

Expected current result:

```text
22 passed
```
