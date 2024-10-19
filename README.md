# OTA-Demo
本プロジェクトでは、Vaultを利用して、想定されるOTAサービスを実現し、デモンストレーションを行いました。


### アプリケーションシナリオ

ある製造企業は多くのモデルのスマートデバイスを製造しており、これらのデバイスで動作するソフトウェアには更新とアップグレードの必要があります。デバイスのソフトウェアはOTA方式で更新され、Vaultを使用して信頼性の高い情報セキュリティを保証しています。本プロジェクトでは、AppRoleを使用して認証を提供し、Policyで認可を行い、Transitを使用して暗号化および復号を実現することで、OTAサービスを実装しました。


### サービスの構成

1. ```ota-init.sh``` は、サービスの実行環境を起動および初期化します。
2. ```ota-client.py``` は、クライアントのコマンドライン操作を実行します。
3. ```ota-server.py``` は、クライアントが呼び出すためのAPIを提供します。


### サービスの特性

1. サービスは複数のロールをサポートしています。サーバーに対応するロールが1つ、各デバイスタイプに対応するロールがそれぞれ1つあります。各ロールには独立した鍵が割り当てられているため、異なるデバイスタイプごとにファイルを異なる鍵で暗号化することが実現されています。
2. サービスは `upload`、`publish`、`withdraw`、`download` の4つのAPIをサポートしており、最初の3つはサーバーロールが必要で、最後の1つはデバイスロールが必要です。
   - `upload` はサーバーロールが必要であり、この機能は `data/origin` にある元ファイルをサーバーの鍵で暗号化し、`data/upload` ディレクトリにアップロードします。
   - `publish` はサーバーロールが必要であり、この機能は `data/upload` にあるファイルをサーバーの鍵で復号し、指定されたデバイスタイプの鍵で再暗号化した後、`data/publish` ディレクトリに保存し、デバイスがダウンロードできるようにします。
   - `withdraw` はサーバーロールが必要であり、指定されたデバイスタイプとバージョンに基づいて `data/publish` ディレクトリからファイルを削除します。
   - `download` はデバイスロールが必要であり、指定されたデバイスタイプとバージョンのファイルを `data/download` ディレクトリにダウンロードします。呼び出し時にはデバイスのシリアル番号を指定する必要があり、これによりサーバー側で特定のデバイスが更新されたかどうかを記録することができます。
3. 以上の各操作が正常に完了した場合、`data/logs` に操作ログが記録されます。

備考：本仕様はデモ目的で想定された要件のため、不備がある可能性がある点にご注意ください。


### サービスの使用

**コードをダウンロードしてPython環境をインストールする。**

```
$ git clone https://github.com/mj8327/ota-demo.git
$ cd ota-demo
$ pip install poetry
$ poetry install
```

**ターミナルウィンドウを開き、実行環境を初期化してください。**

```
$ ./ota-init.sh

[+] Running 2/1
 ✔ Container ota-vault       Removed                                                   0.4s
 ✔ Network ota-demo_default  Removed                                                   0.1s
[+] Running 2/2
 ✔ Network ota-demo_default  Created                                                   0.0s
 ✔ Container ota-vault       Started                                                   0.3s
Starting Vault...
CONTAINER ID   IMAGE                    COMMAND                   CREATED         STATUS         PORTS                    NAMES
c38bbc67f1fc   hashicorp/vault:latest   "docker-entrypoint.s…"   3 seconds ago   Up 3 seconds   0.0.0.0:8200->8200/tcp   ota-vault
Initialize Vault
Save vault-init.json
{
  'clock_skew_ms': 0,
  'cluster_id': 'c60b31db-cb80-77af-6979-edb637d8fcd6',
  'cluster_name': 'vault-cluster-9e18cf7e',
  'echo_duration_ms': 0,
  'enterprise': False,
  'initialized': True,
  'performance_standby': False,
  'replication_dr_mode': 'disabled',
  'replication_performance_mode': 'disabled',
  'replication_primary_canary_age_ms': 0,
  'sealed': False,
  'server_time_utc': 1729334609,
  'standby': False,
  'version': '1.18.0',
}
Create origin/
Delete upload/
Delete publish/
Delete download/
Delete logs/
Create policy: ota-server
Create policy: ota-device
Enable approle: <Response [204]>
Enable transit: <Response [204]>
Create role: server
Create key: server
Create role: model_a
Create key: model_a
Create role: model_b
Create key: model_b
```

**サーバーを起動してください。**

```
$ python ota_server.py

 * Serving Flask app 'ota_server'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
 * Restarting with stat
 * Debugger is active!
 * Debugger PIN: 132-448-830
```

**クライアント機能をテストしてください。**

```
| model   | version | 
|---------|---------|
| model_a |   1.0   |
| model_a |   1.1   |
| model_a |   2.27  |
| model_a |   3.0   |
| model_b |   1.0   |
| model_b |   1.1   |
| model_b |   2.27  |
| model_b |   3.0   |

$ python ota_client.py upload --model model_a --version 1.0
Login as server
{'action': 'upload', 'file': 'model_a_1.0.txt', 'ok': True}

$ python ota_client.py publish --model model_a --version 1.0
Login as server
{'action': 'publish', 'file': 'model_a_1.0.txt', 'ok': True}

$ python ota_client.py publish --model model_a --version 1.0
Login as server
{'error': 'File already published'}

$ python ota_client.py withdraw --model model_a --version 1.0
Login as server
{'action': 'withdraw', 'file': 'model_a_1.0.txt', 'ok': True}

$ python ota_client.py withdraw --model model_a --version 1.0
Login as server
{'error': 'File not found'}

$ python ota_client.py publish --model model_a --version 1.0
Login as server
{'action': 'publish', 'file': 'model_a_1.0.txt', 'ok': True}

$ python ota_client.py download --model model_a --version 1.0 --serial 001
Login as model_a
File saved to data/download/model_a_1.0_001.txt

# ディレクトリ内のファイル
data
├── download
│   └── model_a_1.0_001.txt
├── logs
│   ├── model_a-001-download-20241019112914-model_a_1.0.txt
│   ├── server-publish-20241019112821-model_a_1.0.txt
│   └── server-upload-20241019112815-model_a_1.0.txt
├── origin
│   ├── model_a_1.0.txt
│   ├── model_a_1.1.txt
│   ├── model_a_2.27.txt
│   ├── model_a_3.0.txt
│   ├── model_b_1.0.txt
│   ├── model_b_1.1.txt
│   ├── model_b_2.27.txt
│   └── model_b_3.0.txt
├── publish
│   └── model_a_1.0.txt
├── upload
    └── model_a_1.0.txt
```


### トラブルシューティング

1. ModuleNotFoundError: No module named 'hvac' 

修正
```
$ poetry shell
```
