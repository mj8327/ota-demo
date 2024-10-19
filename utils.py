import base64
import shutil
from pathlib import Path
from dotenv import dotenv_values
from datetime import datetime, UTC


config = dotenv_values('.env') 


DATA_ROOT = Path('./data')

# store files that encrypted by server key
DATA_UPLOAD = DATA_ROOT / 'upload'
DATA_UPLOAD.mkdir(parents=True, exist_ok=True)

# store files that encrypted by device key
DATA_PUBLISH = DATA_ROOT / 'publish'
DATA_PUBLISH.mkdir(parents=True, exist_ok=True)

# store downloaded files that decrypted by device key
DATA_DOWNLOAD = DATA_ROOT / 'download'
DATA_DOWNLOAD.mkdir(parents=True, exist_ok=True)

# store original files
DATA_ORIGIN = DATA_ROOT / 'origin'
DATA_ORIGIN.mkdir(parents=True, exist_ok=True)

# store server logs
DATA_LOGS = DATA_ROOT / 'logs'
DATA_LOGS.mkdir(parents=True, exist_ok=True)


def create_origin_files():
    print('Create origin/')
    for x in ('model_a', 'model_b'):
        for y in ('1.0', '1.1', '2.27', '3.0'):
            with open(DATA_ORIGIN / f'{x}_{y}.txt', 'w') as f:
                f.write(f'This is the update file for device {x} version {y}.')

def clear_working_files():
    for x in (DATA_UPLOAD, DATA_PUBLISH, DATA_DOWNLOAD, DATA_LOGS):
        print(f'Delete {x.name}/')
        if x.exists():
            shutil.rmtree(x)
        x.mkdir(parents=True, exist_ok=True)


def create_approle(client, role_name, policy):
    print(f'Create role: {role_name}')
    result = dict(role=role_name)

    response = client.auth.approle.create_or_update_approle(
        role_name=role_name, token_policies=[policy]
    )
    response = client.auth.approle.read_role_id(role_name=role_name)
    result['role_id'] = response['data']['role_id']

    response = client.auth.approle.generate_secret_id(role_name=role_name)
    result['secret_id'] = response['data']['secret_id']

    return result


def login(client, role_id, secret_id):
    response = client.auth.approle.login(role_id=role_id, secret_id=secret_id)
    return response['auth']['client_token']


def create_transit_key(client, name):
    print(f'Create key: {name}')
    client.secrets.transit.create_key(name=name)


def create_acl_policy(client, name):
    print(f'Create policy: {name}')
    client.sys.create_or_update_acl_policy(
        name=name, 
        policy="""
            path "transit/encrypt/*" {
              capabilities = [ "update" ]
            }

            path "transit/decrypt/*" {
              capabilities = [ "update" ]
            }
        """
    )


def encrypt_data(client, name, plaintext):
    response = client.secrets.transit.encrypt_data(
        name=name, plaintext=base64ify(plaintext),
    )
    return response['data']['ciphertext']


def decrypt_data(client, name, ciphertext, is_hex=False):
    response = client.secrets.transit.decrypt_data(
        name=name, ciphertext=ciphertext,
    )
    output_bytes = base64.b64decode(response['data']['plaintext']).decode('utf-8')
    return bytes.fromhex(output_bytes) if is_hex else output_bytes
    

def encrypt_file(client, name, input_path, output_path):
    with open(input_path, 'rb') as f:
        data = f.read()

    with open(output_path, 'w') as f:
        f.write(encrypt_data(client, name, data))

def decrypt_file(client, name, input_path, output_path):
    with open(input_path, 'r') as f:
        data = f.read()

    with open(output_path, 'wb') as f:
        f.write(decrypt_data(client, name, data, True))


def save_record(role, action, filename, serial=None):
    when = datetime.now(UTC).strftime('%Y%m%d%H%M%S')

    if serial:
        (DATA_LOGS / f'{role}-{action}-{when}-{serial}-{filename}').touch()
    else:
        (DATA_LOGS / f'{role}-{action}-{when}-{filename}').touch()


def base64ify(bytes_or_str):
    if isinstance(bytes_or_str, str):
        input_bytes = bytes_or_str.encode('utf-8')
    else:
        input_bytes = bytes_or_str.hex().encode('utf-8')

    output_bytes = base64.b64encode(input_bytes)
    return output_bytes.decode('ascii')
