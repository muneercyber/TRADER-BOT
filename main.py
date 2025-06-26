import asyncio
import json
from datetime import datetime
from typing import Dict, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)
import po_sniffer
import strategies

# === CONFIGURATION ===
BOT_TOKEN = "7799176242:AAFNZnsgWA7FBR3g2txQADQBR5stDY3cQWM"
ADMIN_ID = 5734178963
ALLOWED_USERS = [ADMIN_ID, 615643589]  # Load from allowed_users.json in production
MIN_CANDLES = 100  # Minimum candles required for analysis
SIGNAL_COOLDOWN = 60  # Seconds between signals

class TradingBot:
    def __init__(self):
        self.sniffer = po_sniffer.PriceSniffer()
        self.strategy = strategies.StrategyEngine()
        self.user_states: Dict[int, dict] = {}  # {user_id: {pair: str, expiry: int}}
        self.signal_lock = asyncio.Lock()  # Prevent duplicate signals

    async def initialize(self):
        """Initialize WebSocket connection"""
        asyncio.create_task(self.sniffer.connect())

    async def validate_user(self, user_id: int) -> bool:
        """Check if user is authorized"""
        return user_id in ALLOWED_USERS

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Telegram /start command handler"""
        if not await self.validate_user(update.effective_user.id):
            await update.message.reply_text("🚫 Unauthorized access")
            return

        keyboard = [
            [InlineKeyboardButton("Crypto", callback_data="cat:crypto")],
            [InlineKeyboardButton("Forex", callback_data="cat:forex")],
            [InlineKeyboardButton("Commodities", callback_data="cat:commodities")],
            [InlineKeyboardButton("Stocks", callback_data="cat:stocks")]
        ]
        await update.message.reply_text(
            "📍 Select asset category:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all callback queries"""
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id

        if not await self.validate_user(user_id):
            await query.edit_message_text("🚫 Unauthorized action")
            return

        if query.data.startswith("cat:"):
            await self._handle_category_selection(query)
        elif query.data.startswith("pair:"):
            await self._handle_pair_selection(query, user_id)
        elif query.data == "back":
            await self._handle_back_button(query)

    async def _handle_category_selection(self, query):
        """Show trading pairs for selected category"""
        category = query.data.split(":")[1]
        pairs = {
            "crypto": ["BTCUSD_otc", "ETHUSD_otc"],
            "forex": ["EURUSD_otc", "GBPUSD_otc"],
            "commodities": ["Gold_otc", "Oil_otc"],
            "stocks": ["AAPL_otc", "TSLA_otc"]
        }.get(category, [])

        buttons = [[InlineKeyboardButton(p, callback_data=f"pair:{p}")] for p in pairs]
        buttons.append([InlineKeyboardButton("↩ Back", callback_data="back")])
        
        await query.edit_message_text(
            "📊 Select pair:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    async def _handle_pair_selection(self, query, user_id: int):
        """Process selected trading pair"""
        pair = query.data.split(":")[1]
        self.user_states[user_id] = {"pair": pair, "expiry": 60}
        self.sniffer.set_pair(pair)  # Activate WebSocket subscription
        
        await query.edit_message_text(f"📍 {pair} selected\n⏳ Collecting data...")
        
        # Check data availability
        prices = self.sniffer.get_prices(pair)
        if len(prices) < MIN_CANDLES:
            await query.edit_message_text(
                f"⚠️ Need {MIN_CANDLES - len(prices)} more candles\n"
                f"Current: {len(prices)}/{MIN_CANDLES}")
            return

        # Generate signal
        async with self.signal_lock:
            signal = self.strategy.analyze(prices[-MIN_CANDLES:])
            if not signal:
                await query.edit_message_text("⚠️ No valid signal detected")
                return

            await query.edit_message_text(
                f"🚀 Signal: {signal['direction']}\n"
                f"📊 Confidence: {signal['confidence']}%\n"
                f"⏳ Expiry: 1 minute")

    async def _handle_back_button(self, query):
        """Return to category selection"""
        await query.edit_message_text(
            "📍 Select asset category:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Crypto", callback_data="cat:crypto")],
                [InlineKeyboardButton("Forex", callback_data="cat:forex")],
                [InlineKeyboardButton("Commodities", callback_data="cat:commodities")],
                [InlineKeyboardButton("Stocks", callback_data="cat:stocks")]
            ]))

async def main():
    """Initialize and run the bot"""
    bot = TradingBot()
    await bot.initialize()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", bot.handle_start))
    app.add_handler(CallbackQueryHandler(bot.handle_callback))

    await app.initialize()
    await app.start()
    print("✅ Bot is running")
    
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await app.stop()

if __name__ == "__main__":
    asyncio.run(main())