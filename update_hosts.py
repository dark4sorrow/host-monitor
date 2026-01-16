import json
import datetime
import pandas as pd
from ping3 import ping
from boxsdk import JWTAuth, Client

# --- DOCKER CONFIGURATION ---
# We will map these paths using the Docker run command
BOX_FILE_ID = '2026233839344'
BOX_CONFIG_PATH = '/app/config.json' 
OUTPUT_JSON_FILE = 'output/hosts_data.json'

def main():
    print(f"--- Starting Container Scan: {datetime.datetime.now()} ---")
    try:
        # Authenticate
        auth = JWTAuth.from_settings_file(BOX_CONFIG_PATH)
        client = Client(auth)
        print("✅ Authenticated")

        # Download & Scan
        df = pd.read_excel(client.file(BOX_FILE_ID).content())
        results = []
        
        for index, row in df.iterrows():
            name = str(row.get('Name', 'Unknown'))
            ip = str(row.get('IP Address', '0.0.0.0'))
            
            if ip.lower() == 'nan' or ip == '0.0.0.0': continue
            
            try:
                is_online = ping(ip, timeout=0.5) is not False
            except:
                is_online = False
                
            status = "online" if is_online else "offline"
            results.append({"id": index+1, "hostname": name, "ip": ip, "status": status})

        # Save
        data = {"last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "hosts": results}
        with open(OUTPUT_JSON_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        print("✅ Data saved.")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
