import os
import json
import logging
from flask import Flask, request, jsonify
import openai

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('llm_service')
app = Flask(__name__)
openai.api_key = os.getenv('OPENAI_API_KEY')

@app.route('/select_url', methods=['POST'])
def select_url():
    data = request.json
    urls = data.get('urls', [])
    visual = data.get('visual_report')
    prompt = f"Given URLs: {urls} and visual report: {visual}, select the single priority URL or null. Respond JSON {'{'}"priority_url": ...}"}
    try:
        resp = openai.ChatCompletion.create(model="gpt-4o", messages=[{"role":"user","content":prompt}])
        result = json.loads(resp.choices[0].message.content)
        logger.info({'event':'select_url_success','url':result.get('priority_url')})
        return jsonify(result),200
    except Exception as e:
        logger.error({'event':'select_url_error','error':str(e)})
        return jsonify({'error':'URL selection failed'}),502

@app.route('/synthesize', methods=['POST'])
def synth():
    bundle = request.json
    prompt = f"Synthesize risk from data: {bundle}. Respond JSON {'{'}\"risk\":...,\"reasoning\":...{'}'}"
    try:
        resp = openai.ChatCompletion.create(model="gpt-4o", messages=[{"role":"user","content":prompt}])
        result = json.loads(resp.choices[0].message.content)
        logger.info({'event':'synthesis_success','risk':result.get('risk')})
        return jsonify(result),200
    except Exception as e:
        logger.error({'event':'synthesis_error','error':str(e)})
        return jsonify({'error':'Synthesis failed'}),502

if __name__=='__main__':
    app.run(host='0.0.0.0', port=5005)