import pychrome
import time
import base64
import json

def decode_frame(data):
    try:
        decoded = base64.b64decode(data).decode("utf-8")
        return json.loads(decoded)
    except Exception as e:
        return None

print("🔗 Connecting to Brave DevTools on port 9222...")
browser = pychrome.Browser(url="http://127.0.0.1:9222")
tabs = browser.list_tab()
if not tabs:
    print("❌ No open tabs found in Brave.")
    exit()

tab = tabs[0]
tab.start()
tab.Network.enable()
print("✅ Connected. Listening for Pocket Option WebSocket data...\n")

def on_ws_frame_received(**kwargs):
    payload = kwargs.get("response", {}).get("payloadData", "")
    if not payload:
        return

    if payload.startswith("42") or payload.startswith("451"):
        print(f"[📡 Event Frame] {payload}")
        return

    decoded = decode_frame(payload)
    if not decoded:
        return

    if isinstance(decoded, list):
        for item in decoded:
            try:
                if len(item) == 3 and isinstance(item[0], str) and item[0].endswith("_otc"):
                    asset, timestamp, price = item
                    print(f"📈 {asset} | Time: {timestamp} | Price: {price}")
            except Exception:
                continue

tab.Network.webSocketFrameReceived = on_ws_frame_received

try:
    while True:
        tab.wait(1)
except KeyboardInterrupt:
    print("\n🛑 Sniffer stopped.")
    tab.stop()
