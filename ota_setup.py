import hvac
import json

from pathlib import Path
from hvac.exceptions import InvalidRequest
from requests.exceptions import ConnectionError
from dotenv import set_key
from beeprint import pp

from utils import (
    config, create_approle, create_transit_key, create_acl_policy, 
    create_origin_files, clear_working_files
)

client = hvac.Client(url=config['VAULT_URL'])


# Do not do this in production
def run():
    init_file = Path('./vault-init.json')
    init_data = None

    if not client.sys.is_initialized():
        print('Initialize Vault')
        init_data = client.sys.initialize(1, 1)

        with open(init_file, 'w') as f:
            print(f'Save {f.name}')
            json.dump(init_data, f, ensure_ascii=False, indent=2)

    if init_data is None:
        if not init_file.exists():
            raise FileNotFoundError(f'File not found: {init_file}')
        
        with open(init_file, 'r') as f:
            print(f'Load {f.name}')
            init_data = json.load(f)

    if client.sys.is_sealed():
        client.sys.submit_unseal_keys(init_data['keys'])

    client.token = init_data['root_token']

    result = client.sys.read_health_status(method='GET')
    pp(result)

    create_origin_files()    
    clear_working_files()

    create_acl_policy(client, 'ota-server')
    create_acl_policy(client, 'ota-device')

    result = client.sys.list_auth_methods()
    if 'approle/' not in result:
        result = client.sys.enable_auth_method(method_type='approle')    
        print(f'Enable approle: {result}')

    result = client.sys.list_mounted_secrets_engines()
    if 'transit/' not in result:
        result = client.sys.enable_secrets_engine(backend_type='transit')
        print(f'Enable transit: {result}')

    for x in ('server', 'model_a', 'model_b'):
        role = create_approle(
            client, x, 'ota-server' if x == 'server' else 'ota-device'
        )
        set_key('.env', f'{x}_role_id'.upper(), role['role_id'])
        set_key('.env', f'{x}_secret_id'.upper(), role['secret_id'])

        create_transit_key(client, x)



if __name__ == '__main__':
    try:
        run()
    except (ConnectionError, ConnectionRefusedError):        
        print('Connect to Vault failed')
    except (InvalidRequest, FileNotFoundError) as e:        
        print(e)
