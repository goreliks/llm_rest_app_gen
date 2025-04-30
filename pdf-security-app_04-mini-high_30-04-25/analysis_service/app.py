import os, base64, logging, re
from io import BytesIO
from flask import Flask, request, jsonify
from pythonjsonlogger import jsonlogger
from PyPDF2 import PdfReader
from pdfminer.high_level import extract_text

app = Flask(__name__)

logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

@app.route('/analyze', methods=['POST'])
def analyze():
    logger.info('Received analysis request')
    data = request.get_json()
    if not data or 'pdf' not in data:
        logger.error('No PDF provided')
        return jsonify(error='No PDF provided'), 400
    try:
        pdf_bytes = base64.b64decode(data['pdf'])
        reader = PdfReader(BytesIO(pdf_bytes))
        logger.info('PDF parsed successfully')
    except Exception as e:
        logger.error('Failed to parse PDF', extra={'error': str(e)})
        return jsonify(error='Failed to parse PDF'), 400

    info = reader.metadata or {}
    metadata = {k: str(v) for k, v in info.items()}

    features = {
        'is_encrypted': reader.is_encrypted,
        'has_javascript': False,
        'has_embedded_files': False,
        'has_forms': False
    }
    try:
        names = reader.trailer['/Root'].get('/Names', {})
        if names.get('/JavaScript'):
            features['has_javascript'] = True
        if names.get('/EmbeddedFiles'):
            features['has_embedded_files'] = True
        if reader.trailer['/Root'].get('/AcroForm'):
            features['has_forms'] = True
    except Exception:
        pass

    urls = []
    try:
        for page in reader.pages:
            annots = page.get('/Annots')
            if annots:
                for a in annots:
                    obj = a.get_object()
                    A = obj.get('/A')
                    if A and '/URI' in A:
                        urls.append(A['/URI'])
    except Exception:
        pass

    try:
        text = extract_text(BytesIO(pdf_bytes))
        logger.info('Text extracted', extra={'length': len(text)})
    except Exception as e:
        text = ''
        logger.error('Text extraction failed', extra={'error': str(e)})

    content_urls = []
    for match in re.finditer(r'(https?://[^\s]+)', text):
        url = match.group(0)
        start, end = match.span()
        context = text[max(0, start-30):min(len(text), end+30)]
        content_urls.append({'url': url, 'context': context})

    structural_report = {'metadata': metadata, 'features': features, 'urls': urls}
    content_report = {'text_summary': text[:200], 'urls': content_urls}

    logger.info('Analysis complete', extra={'struct_urls': len(urls), 'content_urls': len(content_urls)})
    return jsonify(structural_report=structural_report, content_report=content_report)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
