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

@app.route('/synthesize', methods=['POST'])
def synthesize():
    logger.info('Received synthesis request')
    data = request.get_json()
    prompt_system = ('You are a security analyst. Synthesize all findings and produce a final '
                     'risk score (Safe, Low, Medium, High, Malicious) and concise reasoning. '
                     'Respond with JSON {"risk_score": "...", "reasoning": "..."}.')
    prompt_user = json.dumps(data)
    try:
        response = openai.ChatCompletion.create(
            model='gpt-4o',
            messages=[{'role': 'system', 'content': prompt_system},
                      {'role': 'user', 'content': prompt_user}]
        )
        content = response.choices[0].message.content
        result = json.loads(content)
        risk_score = result.get('risk_score')
        reasoning = result.get('reasoning')
        logger.info('Synthesis complete', extra={'risk_score': risk_score})
    except Exception as e:
        logger.error('LLM synthesis failed', extra={'error': str(e)})
        return jsonify(error='LLM synthesis failed', details=str(e)), 502

    return jsonify(risk_score=risk_score, reasoning=reasoning)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
