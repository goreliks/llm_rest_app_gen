import os
import logging
import io
import base64
from flask import Flask, request, jsonify
from pdf2image import convert_from_bytes
import openai

# Logging configuration
log_level = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=log_level)
logger = logging.getLogger("service-visual")

openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

@app.route("/visual", methods=["POST"])
def visual():
    try:
        file = request.files.get("file")
        if not file:
            return jsonify({"error": "No file provided"}), 400
        data = file.read()

        # Convert first page to image
        images = convert_from_bytes(data, first_page=1, last_page=1)
        if not images:
            return jsonify({"error": "Failed to convert PDF to image"}), 500
        img = images[0]

        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_bytes = buffered.getvalue()
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")

        # Create prompt
        prompt = (
            "You are a security analyst. Analyze the following PDF page image.\n"
            "Provide:\n"
            "(a) Apparent Document Type and Purpose\n"
            "(b) Visual Presentation Quality and Tone\n"
            "(c) Key Interactive Elements & Call-to-Action\n"
            "(d) Potential Visual Anomalies or Red Flags\n"
            "Respond with a descriptive analysis."
        )

        # Send to GPT-4o with base64 image
        user_content = f"{prompt}\nImage (base64):\n{img_b64}"
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a security analyst who analyzes PDF page images for deception and anomalies."},
                {"role": "user", "content": user_content}
            ]
        )
        analysis = response.choices[0].message.content

        return jsonify({
            "analysis": analysis,
            "image_base64": img_b64
        }), 200
    except Exception:
        logger.exception("Visual analysis error")
        return jsonify({"error": "Visual analysis error"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003)
