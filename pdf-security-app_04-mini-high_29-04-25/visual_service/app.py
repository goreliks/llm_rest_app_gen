import os
import io
import base64
import logging
from flask import Flask, request, jsonify
from pdf2image import convert_from_bytes
import openai
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('visual_service')
app = Flask(__name__)
openai.api_key = os.getenv('OPENAI_API_KEY')

@app.route('/analyze', methods=['POST'])
def analyze():
    file = request.files.get('file')
    data = file.read()
    # Convert first page
    try:
        images = convert_from_bytes(data, first_page=1, last_page=1)
        img = images[0]
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        logger.info({'event':'image_conversion_success'})
    except Exception as e:
        logger.error({'event':'image_conversion_failure','error':str(e)})
        return jsonify({'error':'Image conversion failed'}),500
    # LLM
    prompt = f"Analyze this image: data:image/png;base64,{img_str} \nRespond JSON with 'type','layout','anomalies','prominent_elements'."
    try:
        resp = openai.ChatCompletion.create(model="gpt-4o", messages=[{"role":"user","content":prompt}])
        content = resp.choices[0].message.content
        report = json.loads(content)
        logger.info({'event':'visual_analysis_success'})
        return jsonify(report),200
    except Exception as e:
        logger.error({'event':'visual_analysis_error','error':str(e)})
        return jsonify({'error':'Visual LLM failed'}),502

if __name__=='__main__':
    app.run(host='0.0.0.0', port=5003)