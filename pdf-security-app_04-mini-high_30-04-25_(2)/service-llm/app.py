import os
import logging
from flask import Flask, request, jsonify
import openai

# Logging configuration
log_level = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=log_level)
logger = logging.getLogger("service-llm")

openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

@app.route("/select_url", methods=["POST"])
def select_url():
    try:
        data = request.get_json()
        struct_urls = data.get("structural_urls", [])
        content_urls = data.get("content_urls", [])
        visual = data.get("visual_report", "")
        prompt = (
            "You are a security analyst. Given the following data:\n"
            f"Structural URLs: {struct_urls}\n"
            f"Content URLs: {content_urls}\n"
            f"Visual Analysis: {visual}\n"
            "Select the single URL that is the most likely primary call-to-action "
            "or the most suspicious target. Respond with only the URL or null."
        )
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a security analyst."},
                {"role": "user", "content": prompt}
            ]
        )
        answer = response.choices[0].message.content.strip()
        if answer.lower() in ["null", "none", ""]:
            priority_url = None
        else:
            priority_url = answer
        return jsonify({"priority_url": priority_url}), 200
    except Exception:
        logger.exception("URL selection error")
        return jsonify({"error": "URL selection error"}), 500

@app.route("/synthesize_risk", methods=["POST"])
def synthesize_risk():
    try:
        data = request.get_json()
        sha256 = data.get("sha256")
        md5 = data.get("md5")
        structural = data.get("structural")
        content = data.get("content")
        visual = data.get("visual")
        file_rep = data.get("file_reputation")
        priority_url = data.get("priority_url")
        url_rep = data.get("url_reputation")
        prompt = (
            "You are a security analyst. Given the following data:\n"
            f"SHA256: {sha256}\n"
            f"MD5: {md5}\n"
            f"Structural Analysis: {structural}\n"
            f"Content Analysis: {content}\n"
            f"Visual Analysis: {visual}\n"
            f"File Reputation: {file_rep}\n"
            f"Priority URL: {priority_url}\n"
            f"URL Reputation: {url_rep}\n"
            "Synthesize a final risk assessment. "
            "Provide a risk score (Safe, Low, Medium, High, Malicious) and a brief reasoning."
        )
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a security analyst."},
                {"role": "user", "content": prompt}
            ]
        )
        content_resp = response.choices[0].message.content.strip()
        parts = content_resp.split("\n", 1)
        risk_score = parts[0]
        reasoning = parts[1] if len(parts) > 1 else ""
        return jsonify({"risk_score": risk_score, "reasoning": reasoning}), 200
    except Exception:
        logger.exception("Risk synthesis error")
        return jsonify({"error": "Risk synthesis error"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5004)
