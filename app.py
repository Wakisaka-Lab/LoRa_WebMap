from flask import Flask, render_template, jsonify
import serial
import serial.tools.list_ports  # 追加: COMポート一覧取得用
import threading
from datetime import datetime
import time
import sys

app = Flask(__name__)

# ==========================================
# 設定とグローバル変数
# ==========================================
BAUD_RATE = 9600
received_points = [] # 受信した座標を溜めるリスト

# 16進数(8桁)を元の小数(float)に戻す関数
def decode_hex_to_float(hex_str):
    val = int(hex_str, 16)
    if val >= 0x80000000:
        val -= 0x100000000
    return val / 100000.0

# ==========================================
# 利用可能なCOMポートを選択する関数
# ==========================================
def select_com_port():
    print("接続されているCOMポートを検索中...")
    ports = list(serial.tools.list_ports.comports())
    
    if not ports:
        print("⚠️ 利用可能なCOMポートが見つかりませんでした。")
        print("LoRaモジュールが正しく接続されているか確認してください。")
        return None
    
    print("\n【利用可能なCOMポート一覧】")
    for i, port in enumerate(ports):
        # デバイス名と説明を表示（例: [0] COM3 - USB Serial Port）
        print(f" [{i}] {port.device} - {port.description}")
        
    print("-" * 40)
    
    while True:
        try:
            choice = input(f"接続するCOMポートの番号 (0-{len(ports)-1}) を入力してください: ")
            index = int(choice)
            if 0 <= index < len(ports):
                selected_port = ports[index].device
                return selected_port
            else:
                print("⚠️ リストにある正しい番号を入力してください。")
        except ValueError:
            print("⚠️ 数値を入力してください。")
        except KeyboardInterrupt:
            print("\nキャンセルされました。")
            return None

# ==========================================
# 裏で動き続けるシリアル通信スレッド
# ==========================================
def serial_loop(port_name):
    try:
        # 選択されたポート名を使って接続
        ser = serial.Serial(port_name, BAUD_RATE, timeout=1)
        print(f"\n✅ [{port_name}] 基地局モジュールに接続しました。受信を待機します...")  
       
        ser.write(b"p2p rx 0\r\n")

        while True:
             
            raw_bytes = ser.readline()
            if not raw_bytes:
                continue
                
            line = raw_bytes.decode('utf-8', errors='ignore').strip()

            if "radio_err_timeout" in line:
                print(f"⚠️ タイムアウト({line})。再度受信待機します。")
                time.sleep(0.5)
                ser.write(b"p2p rx 0\r\n")
                continue

            elif "radio_err" in line:
                print(f"⚠️ 受信エラー({line})。再度受信待機します。")
                time.sleep(0.5)
                ser.write(b"p2p rx 0\r\n")
                continue

            elif "radio_rx" in line:
                print(f"📡 電波キャッチ!: {line}")
                parts = line.split()
                
                # partsの中に16桁の16進数っぽいものがあるか探す
                hex_data = None
                rssi = ""
                snr = ""
                
                for i, p in enumerate(parts):
                    if len(p) == 16:
                        try:
                            # 16進数として変換できるかテスト
                            int(p, 16)
                            hex_data = p
                            # 後ろに続くRSSIとSNRも取得（あれば）
                            if i + 1 < len(parts):
                                rssi = parts[i+1]
                            if i + 2 < len(parts):
                                snr = parts[i+2]
                        except ValueError:
                            pass
                            
                if hex_data:
                    lat = decode_hex_to_float(hex_data[0:8])
                    lon = decode_hex_to_float(hex_data[8:16])
                    now_str = datetime.now().strftime('%H:%M:%S')
                    
                    # データをリストに追加（RSSIとSNRも追加）
                    received_points.append({
                        'lat': lat, 
                        'lon': lon, 
                        'time': now_str,
                        'rssi': rssi,
                        'snr': snr
                    })
                    print(f"  -> 復元成功: 緯度 {lat}, 経度 {lon}, RSSI: {rssi}, SNR: {snr}")
                time.sleep(0.5)
                ser.write(b"p2p rx 0\r\n") 
    except serial.SerialException as e:
        print(f"\n❌ シリアル通信エラー: {port_name} を開けませんでした。")
        print(f"詳細: {e}")
        print("他のアプリケーションがこのポートを使用していないか確認してください。")
    except Exception as e:
        print(f"\n❌ 予期せぬエラー: {e}")

# ==========================================
# FlaskのWebルーティング
# ==========================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/points')
def get_points():
    return jsonify(received_points)

if __name__ == '__main__':
    # 1. まずターミナル上でCOMポートを選択させる
    target_port = select_com_port()
    
    # 2. ポートが選択された場合のみ、スレッドとサーバーを起動する
    if target_port:
        # 引数 target_port を渡してシリアル受信スレッドを起動
        thread = threading.Thread(target=serial_loop, args=(target_port,), daemon=True)
        thread.start()
        
        # Webサーバー起動
        print(f"\n🌍 Webサーバーを起動します。ブラウザで http://127.0.0.1:5000 にアクセスしてください。")
        app.run(host='127.0.0.1', port=5000, debug=False)
    else:
        print("アプリケーションを終了します。")
        sys.exit(1)