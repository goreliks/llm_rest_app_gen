import os, logging
from flask import Flask, request, jsonify
from pythonjsonlogger import jsonlogger
import requests

app = Flask(__name__)
logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

VT_API_KEY = os.environ['VT_API_KEY']

@app.route('/reputation', methods=['POST'])
def reputation():
    logger.info('Received file reputation request')
    data = request.get_json()
    if not data or 'sha256' not in data:
        logger.error('No sha256 provided')
        return jsonify(error='No sha256 provided'), 400

    sha256 = data['sha256']
    url = f'https://www.virustotal.com/api/v3/files/{sha256}'
    headers = {'x-apikey': VT_API_KEY}
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            logger.error('VirusTotal API error', extra={'status_code': resp.status_code})
            return jsonify(error='VirusTotal API error', details=resp.text), 502
        vt_data = resp.json()
        attr = vt_data.get('data', {}).get('attributes', {})
        stats = attr.get('last_analysis_stats', {})
        results = attr.get('last_analysis_results', {})
        malicious = [vendor for vendor, res in results.items() if res.get('category') == 'malicious']
        summary = {
            'last_analysis_stats': stats,
            'malicious_engines': malicious,
            'first_seen': attr.get('first_seen'),
            'last_seen': attr.get('last_seen')
        }
        logger.info('File reputation summary prepared')
    except Exception as e:
        logger.error('VirusTotal request failed', extra={'error': str(e)})
        return jsonify(error='VirusTotal request failed', details=str(e)), 502

    return jsonify(file_reputation=summary)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
