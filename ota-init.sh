#!/bin/bash


docker-compose -f ota-local.yml down
rm -fr data/vault && mkdir -p data/vault
docker-compose -f ota-local.yml up -d

echo "Starting Vault..."
sleep 3
docker ps

python ota_setup.py