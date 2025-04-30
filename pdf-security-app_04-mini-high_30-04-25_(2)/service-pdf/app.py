import os
import logging
import io
import re
from flask import Flask, request, jsonify
from PyPDF2 import PdfReader

# Logging configuration
log_level = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=log_level)
logger = logging.getLogger("service-pdf")

app = Flask(__name__)

URL_REGEX = re.compile(r"https?://[^\s)>\"]+")

@app.route("/structural", methods=["POST"])
def structural():
    try:
        file = request.files.get("file")
        if not file:
            return jsonify({"error": "No file provided"}), 400
        data = file.read()
        reader = PdfReader(io.BytesIO(data))

        # Metadata
        info = reader.metadata
        metadata = {k.lstrip("/"): v for k, v in info.items()} if info else {}

        # Features
        features = {
            "JavaScript": False,
            "EmbeddedFiles": False,
            "Encrypted": reader.is_encrypted,
            "AcroForm": "/AcroForm" in reader.trailer,
            "OpenAction": "/OpenAction" in reader.trailer
        }

        # URLs from annotations
        urls = []
        for page in reader.pages:
            annots = page.get("/Annots") or []
            for annot in annots:
                obj = annot.get_object()
                action = obj.get("/A")
                if action and action.get("/URI"):
                    urls.append(action.get("/URI"))

        # Check raw content for JavaScript or embedded files
        raw = data.decode("latin-1", errors="ignore")
        if "/JavaScript" in raw:
            features["JavaScript"] = True
        if "/EmbeddedFile" in raw:
            features["EmbeddedFiles"] = True

        return jsonify({
            "metadata": metadata,
            "features": features,
            "urls": list(set(urls))
        }), 200
    except Exception:
        logger.exception("Structural analysis error")
        return jsonify({"error": "Structural analysis error"}), 500

@app.route("/content", methods=["POST"])
def content():
    try:
        file = request.files.get("file")
        if not file:
            return jsonify({"error": "No file provided"}), 400
        data = file.read()
        reader = PdfReader(io.BytesIO(data))

        # Extract text
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""

        # Find URLs with context
        urls = []
        for match in URL_REGEX.finditer(text):
            url = match.group(0)
            start = max(match.start() - 30, 0)
            end = min(match.end() + 30, len(text))
            context = text[start:end]
            urls.append({"url": url, "context": context})

        return jsonify({
            "text": text,
            "urls": urls
        }), 200
    except Exception:
        logger.exception("Content extraction error")
        return jsonify({"error": "Content extraction error"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
