import hvac
import json
import tempfile

from pathlib import Path
from flask import Flask, request, jsonify, send_file

from utils import (
    config, DATA_UPLOAD, save_record, encrypt_file, decrypt_file, DATA_PUBLISH
)


client = hvac.Client(url=config['VAULT_URL'])

app = Flask(__name__)


@app.route('/upload', methods=['POST'])
def upload_file():
    token = request.headers.get('X-Vault-Token')
    if not token:
        return jsonify({'error': 'Vault token required'}), 403
    
    client.token = token
    try:
        token_info = client.lookup_token()
        policies = token_info['data']['policies']
        if 'ota-server' not in policies:
            return jsonify({'error': 'Permission denied'}), 403        
    except Exception as e:
        return jsonify({'error': str(e)}), 403
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    file.save(DATA_UPLOAD / file.filename)
    save_record('server', 'upload', file.filename)

    return jsonify({'ok': True, 'action': 'upload', 'file': file.filename}), 200


@app.route('/publish', methods=['POST'])
def publish_file():
    token = request.headers.get('X-Vault-Token')
    if not token:
        return jsonify({'error': 'Vault token required'}), 403
    
    client.token = token
    try:
        token_info = client.lookup_token()
        policies = token_info['data']['policies']
        if 'ota-server' not in policies:
            return jsonify({'error': 'Permission denied'}), 403        
    except Exception as e:
        return jsonify({'error': str(e)}), 403
    
    data = json.loads(request.data)
    model, version = data['model'], data['version']
    src_path = DATA_UPLOAD / f'{model}_{version}.txt'
    pub_path = DATA_PUBLISH / src_path.name

    if not src_path.exists():
        return jsonify({'error': 'File not found'}), 200

    if pub_path.exists():
        return jsonify({'error': 'File already published'}), 200
    
    tmp_path = Path(tempfile.gettempdir()) / src_path.name

    decrypt_file(client, 'server', src_path, tmp_path)

    encrypt_file(client, model, tmp_path,  pub_path)

    save_record('server', 'publish', pub_path.name)

    return jsonify({'ok': True, 'action': 'publish', 'file': pub_path.name}), 200


@app.route('/withdraw', methods=['POST'])
def withdraw_file():
    token = request.headers.get('X-Vault-Token')
    if not token:
        return jsonify({'error': 'Vault token required'}), 403
    
    client.token = token
    try:
        token_info = client.lookup_token()
        policies = token_info['data']['policies']
        if 'ota-server' not in policies:
            return jsonify({'error': 'Permission denied'}), 403        
    except Exception as e:
        return jsonify({'error': str(e)}), 403
    
    data = json.loads(request.data)
    model, version = data['model'], data['version']
    pub_path = DATA_PUBLISH / f'{model}_{version}.txt'

    if not pub_path.exists():
        return jsonify({'error': 'File not found'}), 200

    pub_path.unlink()
    save_record('server', 'withdraw', pub_path.name)

    return jsonify({'ok': True, 'action': 'withdraw', 'file': pub_path.name}), 200


@app.route('/download', methods=['POST'])
def download_file():
    token = request.headers.get('X-Vault-Token')
    if not token:
        return jsonify({'error': 'Vault token required'}), 403
    
    client.token = token
    try:
        token_info = client.lookup_token()
        policies = token_info['data']['policies']
        if 'ota-device' not in policies:
            return jsonify({'error': 'Permission denied'}), 403        
    except Exception as e:
        return jsonify({'error': str(e)}), 403
    
    data = json.loads(request.data)
    model, version, serial = data['model'], data['version'], data['serial']
    pub_path = DATA_PUBLISH / f'{model}_{version}.txt'

    if not pub_path.exists():
        return jsonify({'error': 'File not found'}), 200

    save_record('server', 'download', pub_path.name, serial)

    return send_file(pub_path, as_attachment=True) 


if __name__ == '__main__':
    app.run(debug=True)
