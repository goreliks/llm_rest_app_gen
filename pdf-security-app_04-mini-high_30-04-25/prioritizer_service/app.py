import os, logging, json
from flask import Flask, request, jsonify
from pythonjsonlogger import jsonlogger
import openai

app = Flask(__name__)
logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

openai.api_key = os.environ['OPENAI_API_KEY']

@app.route('/prioritize', methods=['POST'])
def prioritize():
    logger.info('Received prioritization request')
    data = request.get_json()
    structural_urls = data.get('structural_urls', [])
    content_urls = data.get('content_urls', [])
    visual_report = data.get('visual_report', {})
    prompt_system = ('You are a security analyst. Based on structural URLs, content URLs, '
                     'and visual report, select the single URL that is the primary '
                     'call-to-action or most suspicious. Respond with JSON {"priority_url": "..."} '
                     'or {"priority_url": null}.')
    prompt_user = (f'structural_urls: {structural_urls}\n'
                   f'content_urls: {content_urls}\n'
                   f'visual_report: {visual_report}')
    try:
        response = openai.ChatCompletion.create(
            model='gpt-4o',
            messages=[{'role': 'system', 'content': prompt_system},
                      {'role': 'user', 'content': prompt_user}]
        )
        content = response.choices[0].message.content
        result = json.loads(content)
        priority = result.get('priority_url')
        logger.info('Priority URL selected', extra={'priority_url': priority})
    except Exception as e:
        logger.error('LLM prioritization failed', extra={'error': str(e)})
        return jsonify(error='LLM prioritization failed', details=str(e)), 502

    return jsonify(priority_url=priority)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
