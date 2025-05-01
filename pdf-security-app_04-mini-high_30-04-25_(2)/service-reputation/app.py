import os
import logging
import time
from flask import Flask, request, jsonify
import requests

# Logging configuration
log_level = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=log_level)
logger = logging.getLogger("service-reputation")

app = Flask(__name__)

VT_API_KEY = os.getenv("VT_API_KEY")
URLSCAN_API_KEY = os.getenv("URLSCAN_API_KEY")

@app.route("/file", methods=["POST"])
def file_reputation():
    try:
        data = request.get_json()
        sha256 = data.get("sha256")
        if not sha256:
            return jsonify({"error": "No sha256 provided"}), 400
        headers = {"x-apikey": VT_API_KEY}
        resp = requests.get(f"https://www.virustotal.com/api/v3/files/{sha256}", headers=headers)
        if resp.status_code != 200:
            logger.warning(f"VirusTotal response failed — status: {resp.status_code}, body: {resp.text}")
            return jsonify({"error": "Not found in VirusTotal", "status_code": resp.status_code}), 200
        j = resp.json()
        attrs = j.get("data", {}).get("attributes", {})
        stats = attrs.get("last_analysis_stats", {})
        first_seen = attrs.get("first_submission_date")
        last_seen = attrs.get("last_submission_date")
        vendors = attrs.get("last_analysis_results", {})
        top_vendors = {k: v.get("category") for k, v in list(vendors.items())[:5]}
        summary = {
            "stats": stats,
            "first_seen": first_seen,
            "last_seen": last_seen,
            "vendor_results": top_vendors
        }
        return jsonify(summary), 200
    except Exception:
        logger.exception("File reputation error")
        return jsonify({"error": "File reputation error"}), 500

@app.route("/url", methods=["POST"])
def url_reputation():
    try:
        data = request.get_json()
        url = data.get("url")
        if not url:
            return jsonify({"error": "No url provided"}), 400
        headers = {"API-Key": URLSCAN_API_KEY, "Content-Type": "application/json"}
        resp = requests.post("https://urlscan.io/api/v1/scan/", headers=headers, json={"url": url, "public": "on"})
        if resp.status_code not in [200, 201]:
            return jsonify({"error": "urlscan submission failed", "status_code": resp.status_code}), 502
        result = resp.json()
        uuid = result.get("uuid")
        if not uuid:
            return jsonify({"error": "No uuid from urlscan"}), 502
        # Poll for result
        verdicts = {}
        for _ in range(10):
            res2 = requests.get(f"https://urlscan.io/api/v1/result/{uuid}/")
            if res2.status_code == 200:
                jr = res2.json()
                verdicts = jr.get("verdicts", {})
                break
            time.sleep(2)
        summary = {"verdicts": verdicts, "uuid": uuid}
        return jsonify(summary), 200
    except Exception:
        logger.exception("URL reputation error")
        return jsonify({"error": "URL reputation error"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005)
