# PDF Threat Analysis Application

## Architecture Overview

A multi-service RESTful application to analyze PDF files for potential threats, composed of:

- **service-api**: Orchestrates the workflow; entrypoint for API clients.
- **service-pdf**: Performs structural analysis and content extraction of PDFs.
- **service-visual**: Conducts visual analysis of the first PDF page via GPT-4o.
- **service-llm**: Performs priority URL selection and risk synthesis via GPT-4o.
- **service-reputation**: Checks file reputation via VirusTotal and URL reputation via urlscan.io.
- **mongodb**: Stores analysis results.

## Project Structure

```
.
├── docker-compose.yml
├── README.md
├── service-api
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── service-pdf
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── service-visual
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── service-llm
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
└── service-reputation
    ├── app.py
    ├── Dockerfile
    └── requirements.txt
```

## Configuration

Set the following environment variables for API keys:

- `OPENAI_API_KEY`: API key for OpenAI GPT-4o.
- `VT_API_KEY`: API key for VirusTotal.
- `URLSCAN_API_KEY`: API key for urlscan.io.
- `LOG_LEVEL`: (optional) logging level (e.g., INFO, DEBUG).

## Running with Docker Compose

1. Ensure Docker and Docker Compose are installed.
2. In the project root, run:
   ```bash
   docker-compose up --build
   ```
3. Services will start on:
   - **service-api**: http://localhost:5001
   - **service-pdf**: http://localhost:5002
   - **service-visual**: http://localhost:5003
   - **service-llm**: http://localhost:5004
   - **service-reputation**: http://localhost:5005
   - **mongodb**: localhost:27017

## Accessing Logs

Use:

```bash
docker-compose logs -f service-api
```
or replace `service-api` with any service name.

## API Usage Examples

### Analyze PDF via file upload

```bash
curl -X POST -F file=@sample.pdf http://localhost:5001/analyze
```

### Analyze PDF via URL

```bash
curl -X POST -H "Content-Type: application/json" -d '{"url":"http://example.com/sample.pdf"}' http://localhost:5001/analyze
```

### Retrieve Analysis by SHA256

```bash
curl http://localhost:5001/results/<sha256>
```

### List Recent Analyses

```bash
curl http://localhost:5001/results
curl http://localhost:5001/results?limit=5&offset=10
```

## Response Formats

### Successful Analysis Response

```json
{
  "analysis_id": "<object_id>",
  "sha256": "<file_sha256>",
  "risk_score": "Medium",
  "reasoning": "Reasoning text ...",
  "image_base64": "<base64-encoded first page image>"
}
```

### Result Query Response

```json
{
  "analysis_id": "<object_id>",
  "sha256": "<file_sha256>",
  "md5": "<file_md5>",
  "structural": { ... },
  "content": { ... },
  "visual": { "analysis":"...", "image_base64":"..." },
  "file_reputation": { ... },
  "priority_url": "<url or null>",
  "url_reputation": { ... },
  "risk_score": "Medium",
  "reasoning": "Reasoning text ...",
  "image_base64": "<base64 image>"
}
```

### Error Response Example

- 400 Bad Request:

```json
{ "error": "Invalid PDF file" }
```

- 502 Bad Gateway:

```json
{ "error": "Structural analysis failed" }
```

- 500 Internal Server Error:

```json
{ "error": "Internal server error" }
```

- 404 Not Found:

```json
{ "error": "Result not found" }
```