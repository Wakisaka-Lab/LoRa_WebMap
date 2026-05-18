# LoRa WebMap

LoRaモジュール（AL-050 / ADB922S）で受信したGPS座標や電波強度（RSSI）、信号対雑音比（SNR）を、ブラウザ上の地図（OpenStreetMap）にリアルタイムでプロットするWebダッシュボードアプリケーションです。

> **⚠️ 注意**
> 本システムは「受信側（基地局）」のシステムです。GPS座標をLoRaで発信する「送信側（移動局）」のスクリプトについては、**LoRa_field_test** リポジトリ内の `GPS_sent.py` 等を使用してください。

## 機能

* **リアルタイムマッピング**: 受信したGPS座標を即座にLeaflet.jsを使ったWebマップ上にピン留めします。
* **ステータス表示**: 現在の受信パケット数、最終受信時刻、RSSI、SNRの値を画面右上のダッシュボードで確認できます。
* **表示モード切替**: 画面上のラジオボタンから表示モードを切り替え可能です。
    * **リアルタイム**: 最新の現在地ピンのみを表示し、現在位置を追いかけます。
    * **軌跡**: 受信したすべてのピンを表示し、移動ルートを線で結びます。

## 動作環境
* Termux
* Termux-API

* Python 3.x
* **必要なライブラリ**:
    * Flask
    * pyserial

## インストール手順
Termuxの各種環境は、**LoRa_field_test** リポジトリのREADMEで用意していることを想定しています。

ターミナルまたはコマンドプロンプトで、必要なPythonライブラリをインストールします。

```bash
pip install Flask pyserial
```

## 使い方

### 1. シリアルポートの設定

デフォルトでは、Android（Termux + USB Serial Telnet Server）での運用を想定し、TCPポート経由（`socket://127.0.0.1:2323`）でLoRaモジュールと通信するよう設定されています。

Androidで

PC（Windows / Mac / Linux）にUSBで直接LoRaモジュールを接続して使用する場合は、`app.py` 内の以下の行をご自身の環境に合わせて変更してください。

**変更前:**
```python
ser = serial.serial_for_url('socket://127.0.0.1:2323', timeout=1)
```

**変更後（Windowsの例）:**
```python
ser = serial.Serial('COM3', 9600, timeout=1)
```

**変更後（Linux / Macの例）:**
```python
ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
```

### 2. アプリケーションの起動

リポジトリのディレクトリ（`app.py`がある場所）で以下のコマンドを実行し、Flaskサーバーを立ち上げます。同時に裏側でシリアル通信の受信スレッドも起動します。

```bash
python app.py
```

### 3. ブラウザでアクセス

サーバーが起動したら、Webブラウザを開き以下のURLにアクセスしてください。

[http://127.0.0.1:5000](http://127.0.0.1:5000)

> **Tips:**
> 同じWi-Fiネットワークに繋がっている別のスマホやPCから地図を見たい場合は、`app.py` の一番下の行を `app.run(host='0.0.0.0', port=5000, debug=False)` に変更し、ホストPCのローカルIPアドレス（例: `http://192.168.x.x:5000`）でアクセスしてください。

## ファイル構成

* `app.py`: FlaskのWebサーバーおよび、LoRaモジュールと通信して16進数のデータを緯度・経度に復元するバックエンド処理。
* `templates/index.html`: Leaflet.jsを用いたフロントエンド画面。2秒ごとにバックエンドからAPI経由で最新の座標情報を取得して地図を描画します。
