
import hvac
import json
import click
import requests
import tempfile

from pathlib import Path

from utils import (
    config, login, encrypt_file, decrypt_file, DATA_ORIGIN, DATA_DOWNLOAD
)


client = hvac.Client(url=config['VAULT_URL'])


DEVICE_ROLES = ['model_a', 'model_b']


def login_as(role):
    print(f'Login as {role}')
    return login(
        client, 
        config[f'{role.upper()}_ROLE_ID'], 
        config[f'{role.upper()}_SECRET_ID']
    )


@click.group()
def cli():
    pass

@cli.command()
@click.option(
    '--model', type=click.Choice(DEVICE_ROLES), required=True, 
    help="The device model of the file to be uploaded."
)
@click.option(
    '--version', type=str, required=True, 
    help="The version of the file to be uploaded."
)
def upload(model, version):
    src_file = DATA_ORIGIN / f'{model}_{version}.txt'
    if not src_file.exists():
        print(f'File not found: {src_file.name}')
        return
    
    role = 'server'
    vault_token = login_as(role)
    tmp_file = Path(tempfile.gettempdir()) / src_file.name

    encrypt_file(client, role, src_file, tmp_file)

    response = requests.post(
        f'{config["OTA_API_URL"]}/upload', 
        headers={'X-Vault-Token': vault_token},
        files={'file': open(tmp_file, 'rb')},
    )

    response.raise_for_status()
    print(response.json())


@cli.command()
@click.option(
    '--model', type=click.Choice(DEVICE_ROLES), required=True, 
    help="The device model of the file to be published."
)
@click.option(
    '--version', type=str, required=True, 
    help="The version of the file to be published."
)
def publish(model, version):
    role = 'server'
    vault_token = login_as(role)

    response = requests.post(
        f'{config["OTA_API_URL"]}/publish', 
        headers={'X-Vault-Token': vault_token},
        data=json.dumps({'model': model, 'version': version})
    )

    response.raise_for_status()
    print(response.json())


@cli.command()
@click.option(
    '--model', type=click.Choice(DEVICE_ROLES), required=True, 
    help="The device model of the file to be published."
)
@click.option(
    '--version', type=str, required=True, 
    help="The version of the file to be published."
)
def withdraw(model, version):
    role = 'server'
    vault_token = login_as(role)

    response = requests.post(
        f'{config["OTA_API_URL"]}/withdraw', 
        headers={'X-Vault-Token': vault_token},
        data=json.dumps({'model': model, 'version': version})
    )

    response.raise_for_status()
    print(response.json())


@cli.command()
@click.option(
    '--model', type=click.Choice(DEVICE_ROLES), required=True, 
    help="The device model of the file to be download."
)
@click.option(
    '--version', type=str, required=True, 
    help="The version of the file to be download."
)
@click.option(
    '--serial', type=str, required=True, 
    help="The serial no of the device."
)
def download(model, version, serial):
    vault_token = login_as(model)

    response = requests.post(
        f'{config["OTA_API_URL"]}/download', 
        headers={'X-Vault-Token': vault_token},
        data=json.dumps({
            'model': model, 'version': version, 'serial': serial
        })
    )

    response.raise_for_status()

    tmp_file = Path(tempfile.gettempdir()) / f'{model}_{version}_{serial}.txt'
    with open(tmp_file, 'w') as f:
        f.write(response.content.decode('utf-8'))

    out_file = DATA_DOWNLOAD / tmp_file.name

    decrypt_file(client, model, tmp_file, out_file)
    print(f'File saved to {out_file}')


if __name__ == '__main__':
    cli()

