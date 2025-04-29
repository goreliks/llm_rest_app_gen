import os
import json
import logging
from flask import Flask, request, jsonify
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('reputation_service')
app = Flask(__name__)
VT_API_KEY = os.getenv('VT_API_KEY')
URLSCAN_API_KEY = os.getenv('URLSCAN_API_KEY')

@app.route('/file', methods=['POST'])
def file_rep():
    sha256 = request.json.get('sha256')
    headers = {'x-apikey':VT_API_KEY}
    url = f"https://www.virustotal.com/api/v3/files/{sha256}"
    logger.info({'event':'vt_request','sha256':sha256})
    resp = requests.get(url, headers=headers)
    if resp.status_code!=200:
        logger.error({'event':'vt_error','status':resp.status_code})
        return jsonify({'error':'VT request failed'}),502
    data = resp.json()['data']['attributes']
    summary = {'last_analysis_stats':data.get('last_analysis_stats'),'first_seen':data.get('first_submission_date'),'last_seen':data.get('last_submission_date')}
    logger.info({'event':'vt_success'})
    return jsonify(summary),200

@app.route('/url', methods=['POST'])
def url_rep():
    url_t = request.json.get('url')
    headers = {'API-Key':URLSCAN_API_KEY,'Content-Type':'application/json'}
    payload = {'url':url_t}
    logger.info({'event':'urlscan_request','url':url_t})
    resp = requests.post('https://urlscan.io/api/v1/scan/', headers=headers, json=payload)
    if resp.status_code!=200:
        logger.error({'event':'urlscan_error','status':resp.status_code})
        return jsonify({'error':'urlscan failed'}),502
    result = resp.json()
    summary = {'result':result.get('result'),'task':result.get('task')}
    logger.info({'event':'urlscan_success'})
    return jsonify(summary),200

if __name__=='__main__':
    app.run(host='0.0.0.0', port=5004)