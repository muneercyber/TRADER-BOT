import asyncio
import websockets
import json
from collections import deque
from typing import Dict, Deque, Optional

class PriceSniffer:
    def __init__(self):
        self.price_store: Dict[str, Deque[float]] = {}
        self.active_pair: Optional[str] = None
        self.ws_url = "wss://demo-api-eu.po.market"
        self.websocket = None
        self.reconnect_delay = 3  # Seconds between reconnection attempts

    def set_pair(self, pair: str):
        """Set active trading pair and initialize storage"""
        self.active_pair = pair
        if pair not in self.price_store:
            self.price_store[pair] = deque(maxlen=500)  # Store last 500 prices

    def get_prices(self, pair: str) -> list:
        """Get price history for specified pair"""
        return list(self.price_store.get(pair, deque()))

    async def connect(self):
        """Main WebSocket connection loop with auto-reconnect"""
        while True:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    self.websocket = ws
                    print("🔌 WebSocket connected")
                    
                    if self.active_pair:
                        await self._subscribe_pair(self.active_pair)
                    
                    async for message in ws:
                        await self._process_message(message)
                        
            except (websockets.ConnectionClosed, ConnectionError) as e:
                print(f"WebSocket disconnected: {e}. Reconnecting...")
                await asyncio.sleep(self.reconnect_delay)
            except Exception as e:
                print(f"WebSocket error: {e}")
                await asyncio.sleep(self.reconnect_delay)

    async def _subscribe_pair(self, pair: str):
        """Subscribe to price updates for a specific pair"""
        subscribe_msg = {
            "event": "subscribe",
            "params": {"channel": f"quotes/{pair}"}
        }
        await self.websocket.send(json.dumps(subscribe_msg))
        print(f"🔔 Subscribed to {pair}")

    async def _process_message(self, message: str):
        """Process incoming WebSocket message"""
        try:
            data = json.loads(message)
            if "data" in data and "quote" in data["data"]:
                price = float(data["data"]["quote"]["value"])
                if self.active_pair:
                    self.price_store[self.active_pair].append(price)
        except json.JSONDecodeError:
            print("⚠️ Invalid JSON message")
        except KeyError:
            print("⚠️ Unexpected message format")

async def debug_sniffer():
    """Test function for WebSocket connection"""
    sniffer = PriceSniffer()
    sniffer.set_pair("BTCUSD_otc")
    await sniffer.connect()

if __name__ == "__main__":
    asyncio.run(debug_sniffer())