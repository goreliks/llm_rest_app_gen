# PDF Threat Analysis Multi-Service Application

## Architecture Overview

This application consists of multiple Flask-based microservices, orchestrated via Docker Compose:

- api_service (port 5001): Orchestrator, accepts PDF input, coordinates workflow, persists results in MongoDB.
- pdf_processor (port 5002): Validates PDF, computes hashes, extracts structure and content.
- visual_service (port 5003): Converts first PDF page to image, uses OpenAI GPT-4o for visual analysis.
- reputation_service (port 5004): Checks file reputation via VirusTotal and URL reputation via urlscan.io.
- llm_service (port 5005): Interacts with OpenAI GPT-4o for URL prioritization and final risk synthesis.
- mongodb (port 27017): Stores analysis results.

## Project Tree

```
.
├── api_service/
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── pdf_processor/
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── visual_service/
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── reputation_service/
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── llm_service/
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## Configuration

Set the following environment variables (in your shell or `.env` file):

- OPENAI_API_KEY: OpenAI API key for GPT-4o usage.
- VT_API_KEY: VirusTotal API key.
- URLSCAN_API_KEY: urlscan.io API key.
- MONGO_URI: MongoDB connection string (default set in compose).

## Build and Run

1. Build and start services:

   ```bash
   docker-compose up --build -d
   ```

2. Check logs:

   ```bash
   docker-compose logs -f api_service
   ```

3. Stop services:

   ```bash
   docker-compose down
   ```

## API Usage Examples

### 1. Upload PDF File

```bash
curl -X POST http://localhost:5001/analyze \
  -F 'file=@/path/to/sample.pdf' \
  -H 'Content-Type: multipart/form-data'
```

### 2. Submit PDF via URL

```bash
curl -X POST http://localhost:5001/analyze \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com/sample.pdf"}'
```

## Successful Response Format

```json
{
  "analysis_id": "605c3c4f8e3b5a1f4d2f9c3e",
  "risk": "Medium",
  "reasoning": "Detected embedded JavaScript, suspicious URL linking,…"
}
```

## Error Response Examples

- Invalid input:
```json
{ "error": "No file or URL provided" }
```
- PDF validation failure:
```json
{ "error": "Not a valid PDF" }
```
- External API failure:
```json
{ "error": "File reputation check failed" }
```

Check individual service logs for detailed errors and processing steps.