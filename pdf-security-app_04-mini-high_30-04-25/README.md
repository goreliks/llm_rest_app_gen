# PDF Threat Analysis Multi-Service Application

## Architecture Overview

This project consists of multiple Flask-based microservices:

- **api_service**: Orchestrator and main REST API (port 5001).
- **analysis_service**: Structural and content analysis of PDFs (port 5002).
- **visual_service**: Visual analysis using OpenAI GPT-4o (port 5003).
- **vt_service**: File reputation check via VirusTotal API (port 5004).
- **urlscan_service**: URL reputation check via urlscan.io API (port 5006).
- **prioritizer_service**: Priority URL selection using GPT-4o (port 5005).
- **synthesizer_service**: Final risk synthesis using GPT-4o (port 5007).
- **mongodb**: Database for persisting analysis results.

## Project Structure

```
.
├── api_service
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── analysis_service
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── visual_service
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── vt_service
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── urlscan_service
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── prioritizer_service
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── synthesizer_service
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml
└── README.md
```

## Configuration

Required environment variables:

- **OPENAI_API_KEY**: API key for OpenAI GPT-4o.
- **VT_API_KEY**: API key for VirusTotal.
- **URLSCAN_API_KEY**: API key for urlscan.io.
- **MONGODB_URI** (optional): MongoDB connection string (default: `mongodb://mongodb:27017/pdf_analysis`).
- **LOG_LEVEL** (optional): Logging level (default: `INFO`).

Set these in a `.env` file or export before running.

## Building and Running

Use Docker Compose to build and run all services:

```bash
docker-compose up --build
```

This will start all services and MongoDB.

## Accessing Logs

To view logs for a service:

```bash
docker-compose logs -f api_service
```

Replace `api_service` with any service name.

## API Usage

### File Upload

```bash
curl -X POST http://localhost:5001/analyze \
  -F "file=@/path/to/file.pdf"
```

### URL Submission

```bash
curl -X POST http://localhost:5001/analyze \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/file.pdf"}'
```

## Successful Response

```json
{
  "analysis_id": "605c5d5f7c8e4a1b2c3d4e5f",
  "risk_score": "Medium",
  "reasoning": "Detected embedded JavaScript, low VirusTotal detection ratio, and suspicious URL redirection."
}
```

## Error Responses

- **400 Bad Request** (invalid input):

```json
{ "error": "Invalid PDF file" }
```

- **502 Bad Gateway** (external service failure):

```json
{ "error": "Analysis service error", "details": "Connection refused" }
```

- **500 Internal Server Error** (unexpected error):

```json
{ "error": "Internal server error", "details": "Traceback..." }
```