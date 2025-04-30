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

URLSCAN_API_KEY = os.environ['URLSCAN_API_KEY']

@app.route('/reputation', methods=['POST'])
def reputation():
    logger.info('Received URL reputation request')
    data = request.get_json()
    if not data or 'url' not in data:
        logger.error('No URL provided')
        return jsonify(error='No URL provided'), 400

    url_to_scan = data['url']
    api_url = 'https://urlscan.io/api/v1/scan/'
    headers = {'API-Key': URLSCAN_API_KEY, 'Content-Type': 'application/json'}
    payload = {'url': url_to_scan, 'public': 'on'}
    try:
        resp = requests.post(api_url, headers=headers, json=payload)
        if resp.status_code not in (200, 201):
            logger.error('urlscan API error', extra={'status_code': resp.status_code})
            return jsonify(error='urlscan API error', details=resp.text), 502
        us_data = resp.json()
        summary = {'uuid': us_data.get('uuid'), 'result': us_data.get('result')}
        logger.info('URL reputation summary prepared')
    except Exception as e:
        logger.error('urlscan request failed', extra={'error': str(e)})
        return jsonify(error='urlscan request failed', details=str(e)), 502

    return jsonify(url_reputation=summary)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
