#!/usr/bin/env python3
"""
scaffold_with_system_prompt.py

A script to generate and write a multi-service Python application using GPT-4o-mini
with system-prompt injection for JSON-formatted output.

Usage:
    1. Set your OpenAI API key:
       export OPENAI_API_KEY="sk-..."
    2. Run:
       python scaffold_with_system_prompt.py

This will generate:
  - service1/app.py
  - service1/Dockerfile
  - service1/requirements.txt
  - service2/worker.py
  - service2/Dockerfile
  - service2/requirements.txt
  - docker-compose.yml

Ensure you have installed the OpenAI Python client:
    pip install openai
"""
import os
import json
import openai

MODEL = "o4-mini"

# Ensure your environment has OPENAI_API_KEY set
def get_api_key():
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise EnvironmentError("OPENAI_API_KEY environment variable is not set.")
    return key

# Define system and user prompts
SYSTEM_PROMPT = (
    "When you answer, respond only with a JSON object containing a 'files' array, where each item has 'path' and 'content'.\n"
    "Use the example below as a guide, but generate whatever files are needed to fulfill the deliverables exactly.\n"
    "Example schema:\n"
    "```json\n"
    "{\n"
    "  \"files\": [\n"
    "    { \"path\": \"service1_name/app.py\",      \"content\": \"...\" },\n"
    "    { \"path\": \"service1_name/Dockerfile\",  \"content\": \"...\" },\n"
    "    { \"path\": \"README.md\",           \"content\": \"# Project Title\\n\\n...\" }\n"
    "  ]\n"
    "}\n"
    "```\n"
    "No markdown, no extra text — only valid JSON."
)

USER_PROMPT = (
'''
Generate the complete code for a multi-service RESTful application designed to analyze PDF files for potential threats by focusing on detecting anomalies and inconsistencies across structural, content, visual, and reputation data.

**Application Goal & Rationale:**

PDF files are ubiquitous but frequently exploited by attackers for malware delivery and phishing. Standard checks often miss novel threats, sophisticated deceptions, or inconsistencies that indicate malicious intent. This application aims to provide an advanced, automated assessment of a PDF's safety by performing a multi-faceted analysis before user interaction. It specifically looks for contradictions and anomalies between how a PDF looks, what it contains, its underlying structure, and its known reputation, synthesizing these diverse signals into a risk assessment. The goal is to identify suspicious files that might otherwise evade simpler detection methods.

**To achieve this, the application must automate the following process:**

*   **Accept Input:** Provide a REST API endpoint that accepts a PDF file either via direct file upload or by receiving a URL pointing to a publicly accessible PDF.
*   **Validate and Prepare:** Upon receiving input, verify it's a valid PDF file. If invalid, return an appropriate error. If valid, calculate standard cryptographic hashes (MD5, SHA256) of the PDF content.
*   **Check for Prior Analysis:** Before performing a new analysis, check the results database to see if an analysis for the calculated file hash (`SHA256`) already exists. If a result is found, return the previously stored assessment directly. Otherwise, proceed with the full analysis workflow.
*   **Perform Structural Analysis:** Analyze the PDF's internal structure without rendering or executing it to extract:
    *   Basic metadata (Author, Creator application, creation/modification dates, etc.).
    *   Presence of potentially risky features like JavaScript, embedded files, encryption, forms, or non-standard elements.
    *   Any URLs defined structurally within the PDF (e.g., in link annotations or actions).
    *   Output: A structured report of metadata, identified structural features/flags, and any structurally-defined URLs found.
*   **Perform Content Extraction:** Parse the PDF to extract:
    *   The primary raw textual content.
    *   A complete list of all embedded URLs, including, where possible, the associated anchor text or immediate surrounding text for context.
    *   Output: Extracted text summary and a structured list of URLs with their context.
*   **Perform Visual Analysis via GPT-4o:**
    *   Convert at least the first page of the PDF into an image format suitable for visual analysis.
    *   Send the image to the `GPT-4o API`.
    *   Prompt `GPT-4o` to analyze the image(s) acting like a careful observer assessing potential deception, and return a descriptive analysis covering the following aspects:
        *   (a) Apparent Document Type and Purpose: Describe what the document visually appears to be (e.g., invoice, shipping notification, marketing flyer, login page, security warning) and what its primary visual goal or requested user action seems to be.
        *   (b) Visual Presentation Quality and Tone: Assess the overall design quality, professionalism, and visual tone. Comment on layout clarity, consistency (fonts, colors, branding), use of imagery, and any elements suggesting urgency, authority, or generic/low-effort design. Note specific visual elements contributing to this assessment.
        *   (c) Key Interactive Elements & Call-to-Action: Identify the most visually prominent elements intended for user interaction (buttons, links, form fields). Describe their visual styling, text labels, placement, and how strongly they draw the eye. Is there a clear primary call-to-action? How does it relate to the apparent document purpose?
        *   (d) Potential Visual Anomalies or Red Flags: Explicitly point out any visual inconsistencies, anomalies, or elements commonly associated with deception (e.g., blurry logos, mismatched branding, generic stock photos in an unusual context, pixelation, awkward layouts, visual tricks trying to hide or emphasize something, unusually prominent "download" or "login" buttons for the document type).
    *   Output: A descriptive report containing `GPT-4o`'s visual assessment, detailing the points above to provide context for security analysis.
*   **Check File Reputation:** Query the `VirusTotal API` using the file's SHA256 hash. Process the response to generate and retain a concise, structured summary of the file's reputation (e.g., detection ratio, key vendor results, first/last seen dates).
    *   Output: Structured file reputation summary.
*   **Intelligently Select Priority URL via LLM:**
    *   Take the list of URLs with context (from Content Extraction), the list of structurally-defined URLs (from Structural Analysis), and the full visual analysis report (from Visual Analysis via `GPT-4o`).
    *   Send all these pieces of data (both URL lists + visual report) to a separate generative Large Language Model (LLM) API (e.g., `GPT-4o`).
    *   Prompt this LLM specifically to analyze the visual descriptions (especially prominent elements and context) in conjunction with all available extracted URLs (from both structure and text), and select the single URL that represents the most likely primary call-to-action or the most suspicious target the user is being guided towards.
    *   Output: The single selected priority URL string, or null/empty if no clear target is identified.
*   **Conduct Conditional URL Reputation Check:**
    *   If a priority URL was selected in the previous step:
        *   Send only this single priority URL to an external URL scanning service (`urlscan.io API`).
        *   Process the response to get a concise safety assessment (e.g., retrieve scan results like verdicts, malicious indicators, categories).
    *   Output: Structured URL reputation summary (only if performed), otherwise indicate no scan occurred.
*   **Synthesize Findings & Assess Risk via LLM:**
    *   Aggregate all collected data points: the structural report, the content/URL list, the full visual analysis report (from `GPT-4o`), the file reputation summary, the identity of the selected priority URL (if any), and the priority URL's reputation summary (from `urlscan.io`, if scanned).
    *   Send this complete data bundle to another generative Large Language Model (LLM) API (e.g., `GPT-4o`).
    *   Prompt this final LLM to act as a security analyst: synthesize all findings, explicitly look for inconsistencies (e.g., visual type vs. content, visual type vs. structure, anomalies vs. type expectations), weigh the evidence (including direct threats from reputation checks), and generate:
        *   A final risk score (e.g., Safe, Low, Medium, High, Malicious).
        *   A brief, human-readable reasoning summarizing the key findings, especially any detected inconsistencies or critical threats, that justify the score.
    *   Output: Final risk score and reasoning.
*   **Store Results:** Persist the comprehensive analysis results (input details, hashes, all intermediate findings from each step, the selected priority URL, the final LLM assessment, and the base64 encoded image used for visual analysis) in a database.
*   **Return Assessment:** Provide the final risk score, reasoning, and the base64 encoded image used for visual analysis back to the original API caller as a JSON response.
*   **Provide Result Query Capability:** Implement separate API endpoints that allow users to retrieve previously stored analysis results. Support querying by file hash and retrieving all stored results.
*   **Error Handling:** Implement robust error handling throughout the application's workflow. Failures during any step (input validation, external API calls, internal processing, LLM errors) must be logged clearly and result in appropriate HTTP status codes (e.g., 400, 500, 502, 504) and informative JSON error messages returned via the application's REST API.

**Technical Components:**

*   Visual Analysis Model: `OpenAI GPT-4o API`. Use environment variable `OPENAI_API_KEY`.
*   File Reputation Check: `VirusTotal API`. Use environment variable `VT_API_KEY`.
*   Priority URL Selection LLM: OpenAI generative models (e.g., `GPT-4o`). Use environment variable `OPENAI_API_KEY`.
*   URL Reputation Check: `urlscan.io API`. Use environment variable `URLSCAN_API_KEY`.
*   Risk Synthesis LLM: OpenAI generative models (e.g., `GPT-4o`). Use environment variable `OPENAI_API_KEY`.
*   Data Storage: Use `MongoDB` for persisting analysis results.
*   Framework: Use `Python` with `Flask`.
*   Logging: Implement detailed structured logging (e.g., using Python's standard logging module) for all services. Logs should include sufficient details to clearly trace the analysis flow.

**Deliverables Required:**

*   Provide the complete Python source code for all necessary services/components implementing the described logic including comprehensive logging. Determine the optimal service boundaries and communication methods yourself based on the process flow to create a functional multi-service RESTful application.
*   Include `requirements.txt` files listing all Python dependencies for each distinct service/component.
*   Provide `Dockerfiles` for each runnable service/component.
*   Provide a `docker-compose.yml` file to define, configure, and orchestrate the entire multi-service application, including any necessary database services. Ensure that no service attempts to bind to port 5000; use other distinct ports.
*   Provide a straightforward `README.md` file covering:
    *   Architecture overview and project tree. (as generated).
    *   How to organize the provided files (recommended project tree structure).
    *   How to configure the application (listing all required environment variables: `OPENAI_API_KEY`, `VT_API_KEY`, `URLSCAN_API_KEY`, and any logging-related variables).
    *   Step-by-step instructions on how to build and run the multi-service application using Docker Compose.
    *   Basic information on how to access and interpret the logs from the running services.
*   Provide API Usage Examples and Response Format documentation:
    *   Include examples using `curl` demonstrating how to make API calls to trigger the analysis process:
        *   One example showing PDF file upload.
        *   One example showing PDF submission via a public URL.
    *   Include examples using `curl` demonstrating how to query stored results:
        *   One example showing how to retrieve a specific result by its file hash.
        *   One example showing how to retrieve multiple stored results (e.g., all results or a paginated list).
    *   Illustrate the expected JSON structure of a successful analysis API response (showing risk score, reasoning, base64 image, and perhaps a unique analysis ID).
    *   Illustrate the expected JSON structure for the result query endpoints (both single result and multiple results).
    *   Illustrate the expected JSON structure of typical JSON error responses for different failure scenarios (e.g., invalid input, external API failure, internal error, 404 for hash not found).
    '''
)

def generate_manifest():
    openai.api_key = get_api_key()
    response = openai.responses.create(
        model=MODEL,
        input=[
            {"role": "system",  "content": SYSTEM_PROMPT},
            {"role": "user",    "content": USER_PROMPT},
        ],
        reasoning={
            "effort": "high"
        }
    )
    return response.output_text


def write_files(manifest_json: str, base_dir: str = "."):
    try:
        data = json.loads(manifest_json)
    except json.JSONDecodeError as e:
        print("Error: Failed to parse JSON manifest:", e)
        print("Raw response:\n", manifest_json)
        return

    files = data.get("files", [])
    if not files:
        print("Warning: No files found in manifest.")
        return

    for entry in files:
        path = os.path.join(base_dir, entry["path"])
        content = entry["content"]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"⚙️  Wrote {path}")


def main():
    print("🛠️  Generating project manifest from GPT…")
    manifest = generate_manifest()
    print("✅  Manifest received; now writing files…")
    write_files(manifest)
    print("🎉  Done! Your multi-service app is ready.")


if __name__ == "__main__":
    main()
