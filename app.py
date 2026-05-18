from flask import Flask, render_template, jsonify
import serial
import threading
from datetime import datetime
import time

app = Flask(__name__)

# ==========================================
# 設定とグローバル変数
# ==========================================
COM_PORT = 'socket://127.0.0.1:2323'
BAUD_RATE = 9600
received_points = [] # 受信した座標を溜めるリスト

# 16進数(8桁)を元の小数(float)に戻す関数
def decode_hex_to_float(hex_str):
    val = int(hex_str, 16)
    if val >= 0x80000000:
        val -= 0x100000000
    return val / 100000.0

# ==========================================
# 裏で動き続けるシリアル通信スレッド
# ==========================================
def serial_loop():
    try:
        ser = serial.serial_for_url('socket://127.0.0.1:2323', timeout=1)
        print(f"[{COM_PORT}] 基地局モジュールに接続しました。")  
       
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
    except Exception as e:
        print(f"シリアル通信エラー: {e}")

# ==========================================
# FlaskのWebルーティング
# ==========================================
# 1. ブラウザでアクセスしたときに地図画面(HTML)を返す
@app.route('/')
def index():
    return render_template('index.html')

# 2. 地図画面からの「最新データちょうだい」というリクエストに応えるAPI
@app.route('/api/points')
def get_points():
    return jsonify(received_points)

if __name__ == '__main__':
    # Webサーバーを立ち上げる前に、裏でシリアル受信スレッドを起動
    thread = threading.Thread(target=serial_loop, daemon=True)
    thread.start()
    
    # Webサーバー起動 (host='0.0.0.0' にすれば同じWi-Fiの別端末からも見れます)
    app.run(host='127.0.0.1', port=5000, debug=False)
