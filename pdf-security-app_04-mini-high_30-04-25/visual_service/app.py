import os, base64, logging, json
from io import BytesIO
from flask import Flask, request, jsonify
from pythonjsonlogger import jsonlogger
from pdf2image import convert_from_bytes
import openai

app = Flask(__name__)
logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

openai.api_key = os.environ['OPENAI_API_KEY']

@app.route('/analyze', methods=['POST'])
def analyze():
    logger.info('Received visual analysis request')
    data = request.get_json()
    if not data or 'pdf' not in data:
        logger.error('No PDF provided')
        return jsonify(error='No PDF provided'), 400
    try:
        pdf_bytes = base64.b64decode(data['pdf'])
        images = convert_from_bytes(pdf_bytes, first_page=1, last_page=1)
        image = images[0]
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        img_b64 = base64.b64encode(buffer.getvalue()).decode()
        logger.info('Converted first page to image')
    except Exception as e:
        logger.error('Image conversion failed', extra={'error': str(e)})
        return jsonify(error='Image conversion failed', details=str(e)), 500

    prompt_system = ('You are a security analyst. Analyze the following image of a PDF first page. '
                     'Provide a JSON with keys: visual_type, layout, anomalies, prominent_elements.')
    prompt_user = f'data:image/png;base64,{img_b64}'
    try:
        response = openai.ChatCompletion.create(
            model='gpt-4o',
            messages=[{'role': 'system', 'content': prompt_system},
                      {'role': 'user', 'content': prompt_user}]
        )
        content = response.choices[0].message.content
        report = json.loads(content)
        logger.info('Received visual analysis from LLM')
    except Exception as e:
        logger.error('LLM visual analysis failed', extra={'error': str(e)})
        return jsonify(error='LLM visual analysis failed', details=str(e)), 502

    return jsonify(visual_report=report)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
