import os
import io
import json
import logging
from flask import Flask, request, jsonify
import hashlib
from PyPDF2 import PdfReader

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('pdf_processor')
app = Flask(__name__)

@app.route('/process', methods=['POST'])
def process():
    file = request.files.get('file')
    data = file.read()
    # Validate PDF
    if not data.startswith(b'%PDF'):
        logger.error('Invalid PDF')
        return jsonify({'error':'Not a valid PDF'}),400
    # Hashes
    md5 = hashlib.md5(data).hexdigest()
    sha256 = hashlib.sha256(data).hexdigest()
    hashes = {'md5':md5,'sha256':sha256}
    logger.info({'event':'hashes_calculated','hashes':hashes})
    # Structural
    reader = PdfReader(io.BytesIO(data))
    info = reader.metadata
    features = {
        'javascript': '/JavaScript' in reader.trailer.keys(),
        'encrypted': reader.is_encrypted,
        'forms': bool(reader.trailer.get('/AcroForm'))
    }
    struct = {'metadata':{k:str(v) for k,v in info.items()}, 'features':features}
    logger.info({'event':'structural_analysis_done'})
    # Content
    text = ''
    urls=[]
    for page in reader.pages:
        text += page.extract_text() or ''
        # naive URL find
    import re
    for match in re.finditer(r'(https?://\S+)', text):
        urls.append({'url':match.group(1), 'context': text[max(0,match.start()-30):match.end()+30]})
    content = {'text': text[:1000], 'urls': urls}
    logger.info({'event':'content_extraction_done','urls_found':len(urls)})
    return jsonify({'hashes':hashes, 'structural_report':struct, 'content_report':content}),200

if __name__=='__main__':
    app.run(host='0.0.0.0', port=5002)