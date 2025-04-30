import os, base64, hashlib, requests, logging, json
from flask import Flask, request, jsonify
from io import BytesIO
from PyPDF2 import PdfReader
from pythonjsonlogger import jsonlogger
from pymongo import MongoClient

app = Flask(__name__)

# setup logging
logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# service URLs and DB
ANALYSIS_URL = os.environ['ANALYSIS_SERVICE_URL']
VISUAL_URL = os.environ['VISUAL_SERVICE_URL']
VT_URL = os.environ['VT_SERVICE_URL']
PRIORITIZER_URL = os.environ['PRIORITIZER_SERVICE_URL']
URLSCAN_URL = os.environ['URLSCAN_SERVICE_URL']
SYNTHESIZER_URL = os.environ['SYNTHESIZER_SERVICE_URL']
MONGODB_URI = os.environ.get('MONGODB_URI', 'mongodb://mongodb:27017/pdf_analysis')

client = MongoClient(MONGODB_URI)
db = client.get_default_database()
collection = db.analyses

@app.route('/analyze', methods=['POST'])
def analyze():
    logger.info('Received request', extra={'endpoint': '/analyze'})
    try:
        if 'file' in request.files:
            file = request.files['file']
            file_bytes = file.read()
            input_source = 'upload'
            source_name = file.filename
        else:
            data = request.get_json()
            if not data or 'url' not in data:
                logger.error('No file or URL provided')
                return jsonify(error='No file or URL provided'), 400
            pdf_url = data['url']
            logger.info('Downloading PDF', extra={'url': pdf_url})
            r = requests.get(pdf_url)
            if r.status_code != 200:
                logger.error('Failed to download PDF', extra={'status_code': r.status_code})
                return jsonify(error='Failed to download PDF'), 400
            file_bytes = r.content
            input_source = 'url'
            source_name = pdf_url
        # validate PDF
        try:
            reader = PdfReader(BytesIO(file_bytes))
            reader.pages
            logger.info('PDF validation successful')
        except Exception as e:
            logger.error('Invalid PDF file', extra={'error': str(e)})
            return jsonify(error='Invalid PDF file'), 400
        # hashes
        md5 = hashlib.md5(file_bytes).hexdigest()
        sha256 = hashlib.sha256(file_bytes).hexdigest()
        logger.info('Hash calculation', extra={'md5': md5, 'sha256': sha256})
        # encode pdf
        pdf_b64 = base64.b64encode(file_bytes).decode()
        # structural & content
        resp = requests.post(f'{ANALYSIS_URL}/analyze', json={'pdf': pdf_b64})
        if resp.status_code != 200:
            logger.error('Analysis service error', extra={'status_code': resp.status_code, 'body': resp.text})
            return jsonify(error='Analysis service error', details=resp.text), 502
        analysis = resp.json()
        structural = analysis.get('structural_report')
        content = analysis.get('content_report')
        # visual
        resp = requests.post(f'{VISUAL_URL}/analyze', json={'pdf': pdf_b64})
        if resp.status_code != 200:
            logger.error('Visual service error', extra={'status_code': resp.status_code, 'body': resp.text})
            return jsonify(error='Visual service error', details=resp.text), 502
        visual_report = resp.json().get('visual_report')
        # file reputation
        resp = requests.post(f'{VT_URL}/reputation', json={'sha256': sha256})
        if resp.status_code != 200:
            logger.error('VirusTotal service error', extra={'status_code': resp.status_code, 'body': resp.text})
            return jsonify(error='VirusTotal service error', details=resp.text), 502
        file_reputation = resp.json().get('file_reputation')
        # prioritize URL
        urls_struct = structural.get('urls', [])
        urls_content = [u['url'] for u in content.get('urls', [])]
        resp = requests.post(f'{PRIORITIZER_URL}/prioritize', json={'structural_urls': urls_struct, 'content_urls': urls_content, 'visual_report': visual_report})
        if resp.status_code != 200:
            logger.error('Prioritizer service error', extra={'status_code': resp.status_code, 'body': resp.text})
            return jsonify(error='Prioritizer service error', details=resp.text), 502
        priority_url = resp.json().get('priority_url')
        # conditional URL reputation
        url_reputation = None
        if priority_url:
            logger.info('Scanning priority URL', extra={'url': priority_url})
            resp = requests.post(f'{URLSCAN_URL}/reputation', json={'url': priority_url})
            if resp.status_code != 200:
                logger.error('URLScan service error', extra={'status_code': resp.status_code, 'body': resp.text})
                return jsonify(error='URLScan service error', details=resp.text), 502
            url_reputation = resp.json().get('url_reputation')
        # synthesize
        synth_payload = {
            'structural_report': structural,
            'content_report': content,
            'visual_report': visual_report,
            'file_reputation': file_reputation,
            'priority_url': priority_url,
            'url_reputation': url_reputation
        }
        resp = requests.post(f'{SYNTHESIZER_URL}/synthesize', json=synth_payload)
        if resp.status_code != 200:
            logger.error('Synthesizer service error', extra={'status_code': resp.status_code, 'body': resp.text})
            return jsonify(error='Synthesizer service error', details=resp.text), 502
        result = resp.json()
        risk_score = result.get('risk_score')
        reasoning = result.get('reasoning')
        # store in db
        record = {
            'input_source': input_source,
            'source_name': source_name,
            'md5': md5,
            'sha256': sha256,
            'structural_report': structural,
            'content_report': content,
            'visual_report': visual_report,
            'file_reputation': file_reputation,
            'priority_url': priority_url,
            'url_reputation': url_reputation,
            'risk_score': risk_score,
            'reasoning': reasoning
        }
        db_res = collection.insert_one(record)
        analysis_id = str(db_res.inserted_id)
        logger.info('Analysis stored', extra={'analysis_id': analysis_id})
        # response
        response_body = {'analysis_id': analysis_id, 'risk_score': risk_score, 'reasoning': reasoning}
        logger.info('Sending final response', extra=response_body)
        return jsonify(response_body), 200
    except Exception as e:
        logger.exception('Internal server error')
        return jsonify(error='Internal server error', details=str(e)), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
