import os
import io
import requests
import logging
from flask import Flask, request, jsonify
from pymongo import MongoClient
from werkzeug.utils import secure_filename

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('api_service')

# Environment
PDF_PROCESSOR_URL = os.getenv('PDF_PROCESSOR_URL', 'http://pdf_processor:5002/process')
VISUAL_ANALYSIS_URL = os.getenv('VISUAL_ANALYSIS_URL', 'http://visual_service:5003/analyze')
REPUTATION_URL = os.getenv('REPUTATION_URL', 'http://reputation_service:5004/file')
URL_REPUTATION_URL = os.getenv('URL_REPUTATION_URL', 'http://reputation_service:5004/url')
LLM_SELECT_URL = os.getenv('LLM_SELECT_URL', 'http://llm_service:5005/select_url')
LLM_SYNTH_URL = os.getenv('LLM_SYNTH_URL', 'http://llm_service:5005/synthesize')
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://mongodb:27017')

# Mongo
client = MongoClient(MONGO_URI)
db = client.pdf_analysis

app = Flask(__name__)

@app.route('/analyze', methods=['POST'])
def analyze():
    logger.info({'event':'request_received'})
    # Get file or URL
    file = None
    if 'file' in request.files:
        file = request.files['file']
        data = file.read()
        filename = secure_filename(file.filename)
        logger.info({'event':'file_upload', 'filename':filename})
    elif request.json and request.json.get('url'):
        pdf_url = request.json['url']
        logger.info({'event':'download_started','url':pdf_url})
        resp = requests.get(pdf_url)
        if resp.status_code != 200:
            logger.error({'event':'download_failed','status':resp.status_code})
            return jsonify({'error':'Unable to download PDF'}),400
        data = resp.content
        filename = pdf_url.split('/')[-1]
        logger.info({'event':'download_success','filename':filename})
    else:
        logger.error({'event':'invalid_input'})
        return jsonify({'error':'No file or URL provided'}),400
    # Process PDF
    files = {'file': (filename, io.BytesIO(data), 'application/pdf')}
    pdf_proc = requests.post(PDF_PROCESSOR_URL, files=files)
    if pdf_proc.status_code !=200:
        logger.error({'event':'pdf_processor_error','status':pdf_proc.status_code})
        return jsonify({'error':'PDF processing failed'}),502
    pdf_res = pdf_proc.json()
    # Visual
    vis_resp = requests.post(VISUAL_ANALYSIS_URL, files=files)
    if vis_resp.status_code!=200:
        logger.error({'event':'visual_analysis_error','status':vis_resp.status_code})
        return jsonify({'error':'Visual analysis failed'}),502
    visual = vis_resp.json()
    # File reputation
    rep_resp = requests.post(REPUTATION_URL, json={'sha256':pdf_res['hashes']['sha256']})
    if rep_resp.status_code!=200:
        logger.error({'event':'file_reputation_error','status':rep_resp.status_code})
        return jsonify({'error':'File reputation check failed'}),502
    file_rep = rep_resp.json()
    # URL selection
    select_resp = requests.post(LLM_SELECT_URL, json={'urls':pdf_res['urls'],'visual_report':visual})
    if select_resp.status_code!=200:
        logger.error({'event':'url_selection_error','status':select_resp.status_code})
        return jsonify({'error':'URL selection failed'}),502
    priority_url = select_resp.json().get('priority_url')
    url_rep=None
    if priority_url:
        logger.info({'event':'scanning_priority_url','url':priority_url})
        urlscan_resp = requests.post(URL_REPUTATION_URL, json={'url':priority_url})
        if urlscan_resp.status_code==200:
            url_rep = urlscan_resp.json()
        else:
            logger.error({'event':'url_reputation_error','status':urlscan_resp.status_code})
    # Synthesis
    synth_payload = {
        'structural_report': pdf_res['structural_report'],
        'content_report': pdf_res['content_report'],
        'visual_report': visual,
        'file_reputation': file_rep,
        'priority_url': priority_url,
        'url_reputation': url_rep
    }
    synth_resp = requests.post(LLM_SYNTH_URL, json=synth_payload)
    if synth_resp.status_code!=200:
        logger.error({'event':'synthesis_error','status':synth_resp.status_code})
        return jsonify({'error':'Risk synthesis failed'}),502
    final = synth_resp.json()
    # Store
    record = {
        'filename':filename,'hashes':pdf_res['hashes'],
        'structural_report':pdf_res['structural_report'],
        'content_report':pdf_res['content_report'],
        'visual_report':visual,'file_reputation':file_rep,
        'priority_url':priority_url,'url_reputation':url_rep,
        'final':final
    }
    res = db.reports.insert_one(record)
    logger.info({'event':'record_stored','id':str(res.inserted_id)})
    # Response
    response = {'analysis_id': str(res.inserted_id), 'risk':final['risk'], 'reasoning':final['reasoning']}
    logger.info({'event':'response_sent','analysis_id':str(res.inserted_id)})
    return jsonify(response),200

if __name__=='__main__':
    app.run(host='0.0.0.0', port=5001)