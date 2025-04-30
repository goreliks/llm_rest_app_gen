import os
import logging
import hashlib
from flask import Flask, request, jsonify
import requests
from pymongo import MongoClient

# Logging configuration
log_level = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=log_level)
logger = logging.getLogger("service-api")

app = Flask(__name__)

# MongoDB configuration
mongo_uri = os.getenv("MONGO_URI", "mongodb://mongodb:27017/")
client = MongoClient(mongo_uri)
db = client.pdf_analyzer
results_col = db.results

# Service URLs
PDF_SERVICE_URL = os.getenv("PDF_SERVICE_URL", "http://service-pdf:5002")
VISUAL_SERVICE_URL = os.getenv("VISUAL_SERVICE_URL", "http://service-visual:5003")
REPUTATION_SERVICE_URL = os.getenv("REPUTATION_SERVICE_URL", "http://service-reputation:5005")
LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "http://service-llm:5004")

@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        # Accept input
        if request.files.get("file"):
            file = request.files["file"]
            pdf_bytes = file.read()
        else:
            data = request.get_json() or {}
            pdf_url = data.get("url")
            if not pdf_url:
                return jsonify({"error": "No file or URL provided"}), 400
            resp = requests.get(pdf_url, timeout=10)
            if resp.status_code != 200:
                return jsonify({"error": "Failed to download PDF", "status_code": resp.status_code}), 400
            pdf_bytes = resp.content

        # Validate PDF
        if not pdf_bytes.startswith(b"%PDF"):
            return jsonify({"error": "Invalid PDF file"}), 400

        # Calculate hashes
        md5 = hashlib.md5(pdf_bytes).hexdigest()
        sha256 = hashlib.sha256(pdf_bytes).hexdigest()
        logger.info("PDF received", extra={"md5": md5, "sha256": sha256})

        # Check prior analysis
        existing = results_col.find_one({"sha256": sha256})
        if existing:
            logger.info("Returning cached result", extra={"sha256": sha256})
            return jsonify({
                "analysis_id": str(existing["_id"]),
                "sha256": sha256,
                "risk_score": existing["risk_score"],
                "reasoning": existing["reasoning"],
                "image_base64": existing["image_base64"]
            }), 200

        # Structural analysis
        struct_resp = requests.post(f"{PDF_SERVICE_URL}/structural", files={"file": ("file.pdf", pdf_bytes)})
        if struct_resp.status_code != 200:
            logger.error("Structural analysis failed", extra={"status_code": struct_resp.status_code})
            return jsonify({"error": "Structural analysis failed"}), 502
        structural_data = struct_resp.json()

        # Content extraction
        content_resp = requests.post(f"{PDF_SERVICE_URL}/content", files={"file": ("file.pdf", pdf_bytes)})
        if content_resp.status_code != 200:
            logger.error("Content extraction failed", extra={"status_code": content_resp.status_code})
            return jsonify({"error": "Content extraction failed"}), 502
        content_data = content_resp.json()

        # Visual analysis
        visual_resp = requests.post(f"{VISUAL_SERVICE_URL}/visual", files={"file": ("file.pdf", pdf_bytes)})
        if visual_resp.status_code != 200:
            logger.error("Visual analysis failed", extra={"status_code": visual_resp.status_code})
            return jsonify({"error": "Visual analysis failed"}), 502
        visual_data = visual_resp.json()
        image_base64 = visual_data.get("image_base64")

        # File reputation
        file_rep_resp = requests.post(f"{REPUTATION_SERVICE_URL}/file", json={"sha256": sha256})
        if file_rep_resp.status_code != 200:
            logger.error("File reputation check failed", extra={"status_code": file_rep_resp.status_code})
            return jsonify({"error": "File reputation check failed"}), 502
        file_rep_data = file_rep_resp.json()

        # Priority URL selection
        url_select_resp = requests.post(
            f"{LLM_SERVICE_URL}/select_url",
            json={
                "structural_urls": structural_data.get("urls", []),
                "content_urls": content_data.get("urls", []),
                "visual_report": visual_data.get("analysis", "")
            }
        )
        if url_select_resp.status_code != 200:
            logger.error("URL selection failed", extra={"status_code": url_select_resp.status_code})
            return jsonify({"error": "URL selection failed"}), 502
        priority_url = url_select_resp.json().get("priority_url")

        # URL reputation if needed
        url_rep_data = None
        if priority_url:
            url_rep_resp = requests.post(f"{REPUTATION_SERVICE_URL}/url", json={"url": priority_url})
            if url_rep_resp.status_code != 200:
                logger.error("URL reputation check failed", extra={"status_code": url_rep_resp.status_code})
                return jsonify({"error": "URL reputation check failed"}), 502
            url_rep_data = url_rep_resp.json()

        # Risk synthesis
        synth_resp = requests.post(
            f"{LLM_SERVICE_URL}/synthesize_risk",
            json={
                "sha256": sha256,
                "md5": md5,
                "structural": structural_data,
                "content": content_data,
                "visual": visual_data,
                "file_reputation": file_rep_data,
                "priority_url": priority_url,
                "url_reputation": url_rep_data
            }
        )
        if synth_resp.status_code != 200:
            logger.error("Risk synthesis failed", extra={"status_code": synth_resp.status_code})
            return jsonify({"error": "Risk synthesis failed"}), 502
        synth_data = synth_resp.json()
        risk_score = synth_data.get("risk_score")
        reasoning = synth_data.get("reasoning")

        # Store results
        record = {
            "md5": md5,
            "sha256": sha256,
            "structural": structural_data,
            "content": content_data,
            "visual": visual_data,
            "file_reputation": file_rep_data,
            "priority_url": priority_url,
            "url_reputation": url_rep_data,
            "risk_score": risk_score,
            "reasoning": reasoning,
            "image_base64": image_base64
        }
        inserted = results_col.insert_one(record)
        logger.info("Analysis stored", extra={"sha256": sha256, "id": str(inserted.inserted_id)})

        return jsonify({
            "analysis_id": str(inserted.inserted_id),
            "sha256": sha256,
            "risk_score": risk_score,
            "reasoning": reasoning,
            "image_base64": image_base64
        }), 200

    except Exception:
        logger.exception("Analysis error")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/results/<sha256>", methods=["GET"])
def get_result(sha256):
    try:
        result = results_col.find_one({"sha256": sha256})
        if not result:
            return jsonify({"error": "Result not found"}), 404
        result["analysis_id"] = str(result["_id"])
        del result["_id"]
        return jsonify(result), 200
    except Exception:
        logger.exception("Get result error")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/results", methods=["GET"])
def list_results():
    try:
        limit = int(request.args.get("limit", 10))
        offset = int(request.args.get("offset", 0))
        cursor = results_col.find().skip(offset).limit(limit)
        results = []
        for doc in cursor:
            doc["analysis_id"] = str(doc["_id"])
            del doc["_id"]
            results.append(doc)
        return jsonify({"results": results}), 200
    except Exception:
        logger.exception("List results error")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
