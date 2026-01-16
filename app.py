import json
import datetime
import io
import pandas as pd
from ping3 import ping
from boxsdk import JWTAuth, Client
from flask import Flask, make_response, jsonify, render_template, request
import threading
import os

app = Flask(__name__)

# CONFIG
OUTPUT_JSON_FILE = '/app/output/hosts_data.json'
DEFAULT_BOX_FILE_ID = '2026233839344'
BOX_CONFIG_PATH = '/app/config.json'

is_scanning = False
scan_lock = threading.Lock()
last_error = None

def get_box_client():
    return Client(JWTAuth.from_settings_file(BOX_CONFIG_PATH))

def parse_excel_content(file_content):
    df = pd.read_excel(io.BytesIO(file_content), engine='openpyxl')
    df.columns = [str(c).strip().lower() for c in df.columns]
    c_map = {}
    for col in df.columns:
        if 'ip address' in col: c_map['ip'] = col
        elif 'name' in col: c_map['name'] = col
        elif 'operating' in col or 'os' == col: c_map['os'] = col
        elif 'edr' in col: c_map['edr'] = col
        elif 'owner' in col: c_map['owner'] = col
    return df, c_map

def run_scan(file_id):
    global is_scanning, last_error
    if not scan_lock.acquire(blocking=False):
        print("DEBUG LOG: Scan already running.", flush=True)
        return
    try:
        is_scanning = True
        last_error = None
        print(f"DEBUG LOG: Starting scan for ID: {file_id}", flush=True)
        client = get_box_client()
        
        try:
            box_file = client.file(file_id).get()
        except Exception as box_err:
            last_error = f"Access Denied: Box File ID {file_id} not found or inaccessible."
            print(f"DEBUG LOG ERROR: {last_error}", flush=True)
            return

        content = box_file.content()
        df, col_map = parse_excel_content(content)

        results = []
        for i, row in df.iterrows():
            ip = str(row.get(col_map.get('ip'), ''))
            if not ip or ip.lower() == 'nan': continue
            
            edr = str(row.get(col_map.get('edr'), ''))
            is_online = False
            if 'boneyard' not in (ip + edr).lower():
                try:
                    is_online = ping(ip, timeout=0.1) is not False
                except: pass

            results.append({
                "id": i+1,
                "hostname": str(row.get(col_map.get('name'), 'Unknown')),
                "ip": ip,
                "os": str(row.get(col_map.get('os'), 'Unknown')),
                "edr": edr if edr.lower() != 'nan' else 'Unknown',
                "owner": str(row.get(col_map.get('owner'), 'Unknown')),
                "status": "online" if is_online else "offline"
            })

        out_data = {
            "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "file_id": file_id,
            "filename": box_file.name,
            "hosts": results,
            "error": None
        }
        
        with open(OUTPUT_JSON_FILE, 'w') as f:
            json.dump(out_data, f, indent=4)
        print(f"DEBUG LOG: Scan saved successfully: {out_data['last_updated']}", flush=True)

    except Exception as e:
        last_error = str(e)
        print(f"DEBUG LOG ERROR: {last_error}", flush=True)
    finally:
        is_scanning = False
        scan_lock.release()

@app.route('/')
def index(): return render_template('index.html')

@app.route('/api')
def api():
    if not os.path.exists(OUTPUT_JSON_FILE):
        return jsonify({"last_updated": "Never", "hosts": [], "error": last_error})
    with open(OUTPUT_JSON_FILE, 'r') as f:
        data = json.load(f)
        data['error'] = last_error
        return jsonify(data)

@app.route('/api/auth_info')
def auth_info():
    """Returns the Service Account Email needed for folder sharing."""
    try:
        client = get_box_client()
        me = client.user().get()
        return jsonify({"email": me.login, "name": me.name})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/rescan')
def rescan():
    fid = request.args.get('file_id', DEFAULT_BOX_FILE_ID)
    threading.Thread(target=run_scan, args=(fid,)).start()
    return jsonify({"status": "started"})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)