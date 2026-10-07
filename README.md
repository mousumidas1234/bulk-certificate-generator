# Bulk Certificate Generator

## Overview

Bulk Certificate Generator is a FastAPI backend that accepts one event and a list of recipients, creates a tracked generation job, and produces one PDF certificate per recipient.

## Features

- Pydantic validation for event and recipient data
- Bulk job submission with progress and per-recipient results
- Background processing using FastAPI `BackgroundTasks`
- Per-recipient failure isolation: one rendering failure does not stop the job
- SQLite and SQLAlchemy persistence by default
- A single professional ReportLab certificate template
- PDF download endpoints and automated tests

## Tech Stack

Python 3.11+, FastAPI, SQLAlchemy 2, SQLite, Pydantic 2, ReportLab, pytest, and httpx.

## Project Structure

`app/routes` contains HTTP endpoints, `app/services` contains job processing, `app/templates` contains the fixed PDF design, and `app/models.py` / `app/schemas.py` contain persistence and API contracts. Generated PDFs are kept in `generated/<job-id>/`; only their paths and metadata are stored in SQLite.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

The application reads environment variables directly and does not load `.env` files automatically. The defaults work without configuration. To customize a local run, export variables before starting the application:

```bash
export DATABASE_URL="sqlite:///./certificates.db"
export GENERATED_DIR="./generated"
export LOG_LEVEL="INFO"
```

On Windows PowerShell:

```powershell
$env:DATABASE_URL = "sqlite:///./certificates.db"
$env:GENERATED_DIR = ".\\generated"
$env:LOG_LEVEL = "INFO"
```

`.env.example` documents the available variables, but copying it to `.env` alone does not apply them.

## Running the Application

```bash
uvicorn app.main:app --reload
```

Interactive Swagger UI is available at http://127.0.0.1:8000/docs.

## Running Tests

```bash
pytest
```

Tests use a temporary SQLite database and temporary generated-file directory, so they do not depend on a separate database or leave certificates in the repository.

## API Usage

Submit one bulk job:

```bash
curl -X POST http://127.0.0.1:8000/api/jobs \
  -H 'Content-Type: application/json' \
  -d '{
    "event_name": "Python Workshop 2026",
    "event_date": "2026-10-07",
    "recipients": [
      {"name": "Mousumi Das", "email": "mousumi@example.com"},
      {"name": "Rahul Sharma", "email": "rahul@example.com"}
    ]
  }'
```

Example response (`202 Accepted`):

```json
{"job_id": 1, "status": "pending", "total": 2, "successful": 0, "failed": 0, "processed": 0, "progress": 0, "certificates": []}
```

Check job status and progress:

```bash
curl http://127.0.0.1:8000/api/jobs/1
```

List the job's recipient results:

```bash
curl http://127.0.0.1:8000/api/jobs/1/certificates
```

Download a successful certificate:

```bash
curl -OJ http://127.0.0.1:8000/api/certificates/1
```

## Bulk Processing

The request contains the complete recipient list, so clients submit one job rather than making one request per certificate. The service iterates over recipients and commits each result, making progress visible and keeping already-completed work durable.

Duplicate recipients are allowed. Each entry in the submitted list is treated independently and produces its own certificate result.

## Failure Handling

Input errors reject the entire request with a clear `422` response. Runtime PDF errors are caught around the individual recipient, stored as a failed certificate result with a safe public message, and processing continues. A job with at least one failure ends as `completed_with_errors`.

## Design Decisions

- FastAPI provides typed request validation, OpenAPI documentation, and lightweight background tasks.
- SQLAlchemy keeps persistence independent of route code and makes SQLite easy to replace with another relational database.
- SQLite is the default for zero-setup local execution.
- BackgroundTasks returns a job ID quickly while keeping infrastructure simple for this assignment. A durable queue would be appropriate for very large production workloads.
- PDFs are stored as files rather than database blobs; the database stores safe generated paths and result metadata.
- One fixed template meets the assignment scope and keeps the certificate generator easy to understand and test.
- The certificate template uses `fc-match` to discover a system TrueType font when available. If font discovery is unavailable, it falls back to ReportLab's standard Helvetica fonts, which reliably cover normal Latin/WinAnsi text but do not guarantee support for every Unicode script.

## Limitations / Future Improvements

FastAPI in-process background tasks are not a durable distributed queue, and this version has no authentication, rate limiting, or cleanup policy for old files. A production deployment could add a worker queue, object storage, authentication, and retention management.
