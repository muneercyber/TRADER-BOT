import asyncio
import nest_asyncio
import json
import os
import subprocess
import time
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler
)

nest_asyncio.apply()  # Allows nested event loops

# === Telegram Bot Setup ===
BOT_TOKEN = "7799176242:AAFNZnsgWA7FBR3g2txQADQBR5stDY3cQWM"
ADMIN_ID = 5734178963
ALLOWED_USERS_FILE = "allowed_users.json"
EXPIRIES = ["5s", "15s", "30s", "60s"]

# === Globals ===
user_states = {}
user_assets = {}
user_expiry = {}
running_users = set()

# === Ensure allowed_users.json exists ===
if not os.path.exists(ALLOWED_USERS_FILE):
    with open(ALLOWED_USERS_FILE, "w") as f:
        json.dump([ADMIN_ID, 615643589], f)

with open(ALLOWED_USERS_FILE) as f:
    allowed_users = json.load(f)

# === WebSocket + Sniffer + Strategies ===
def start_background_services():
    subprocess.Popen(["python", "po_bot.py"])
    subprocess.Popen(["python", "po_sniffer.py"])

# === UI Buttons ===
def get_main_buttons():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("▶️ Start", callback_data="start_bot"),
        InlineKeyboardButton("⛔ Stop", callback_data="stop_bot"),
        InlineKeyboardButton("👮 Admin Panel", callback_data="admin")
    ]])

def get_category_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💹 Crypto", callback_data="cat_crypto"),
         InlineKeyboardButton("💱 Forex", callback_data="cat_forex")],
        [InlineKeyboardButton("🛢️ Commodities", callback_data="cat_commodities"),
         InlineKeyboardButton("🏢 Stocks", callback_data="cat_stocks")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
    ])

def get_expiry_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{t}", callback_data=f"expiry_{t}") for t in EXPIRIES],
        [InlineKeyboardButton("🔙 Back", callback_data="select_pair")]
    ])

# === OTC Lists ===
OTC_PAIRS = {
    "cat_crypto": ["BTCUSD_otc", "ETHUSD_otc", "SOLUSD_otc", "XRPUSD_otc", "LTCUSD_otc",
                   "BNBUSD_otc", "DOGEUSD_otc", "ADAUSD_otc", "TRXUSD_otc", "DOTUSD_otc"],
    "cat_forex": ["EURUSD_otc", "GBPUSD_otc", "USDJPY_otc", "AUDUSD_otc", "NZDUSD_otc",
                  "USDCHF_otc", "USDCAD_otc", "EURGBP_otc", "GBPJPY_otc", "AUDJPY_otc"],
    "cat_commodities": ["GOLD_otc", "SILVER_otc", "CRUDE_otc", "PLATINUM_otc", "NATGAS_otc"],
    "cat_stocks": ["AAPL_otc", "TSLA_otc", "AMZN_otc", "MSFT_otc", "META_otc"]
}

# === Command Handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in allowed_users:
        return await update.message.reply_text("❌ You're not authorized.")

    user_states[uid] = False
    await context.bot.send_message(
        chat_id=uid,
        text="✅ Select asset:",
        reply_markup=get_main_buttons()
    )
    await context.bot.set_chat_permissions(
        chat_id=update.effective_chat.id,
        permissions=ChatPermissions(can_send_messages=uid == ADMIN_ID)
    )

# === Button Logic ===
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    if uid not in allowed_users:
        return await query.edit_message_text("❌ Access denied.")

    data = query.data

    if data == "start_bot":
        user_states[uid] = True
        await query.edit_message_text("⚙️ Bot started. Choose a category:",
                                      reply_markup=get_category_buttons())
    elif data == "stop_bot":
        user_states[uid] = False
        await query.edit_message_text("🛑 Bot stopped.", reply_markup=get_main_buttons())
    elif data.startswith("cat_"):
        category = data
        pairs = OTC_PAIRS.get(category, [])
        buttons = [[InlineKeyboardButton(pair, callback_data=f"pair_{pair}")]
                   for pair in pairs]
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_main")])
        await query.edit_message_text(f"📈 Select pair from {category[4:].title()}",
                                      reply_markup=InlineKeyboardMarkup(buttons))
    elif data.startswith("pair_"):
        if not user_states.get(uid):
            return await query.edit_message_text("❌ Please press Start first.")
        pair = data[5:]
        user_assets[uid] = pair
        await query.edit_message_text(f"⏰ Now choose expiry time for {pair}",
                                      reply_markup=get_expiry_buttons())
    elif data.startswith("expiry_"):
        expiry = data[7:]
        user_expiry[uid] = expiry
        asset = user_assets.get(uid)
        await query.edit_message_text(f"✅ Pair set: {asset} | ⏰ {expiry}")
        await send_signal(context, uid, asset, expiry)
    elif data == "admin":
        await query.edit_message_text(f"👮 Admin ID: {ADMIN_ID}")
    elif data == "back_main":
        await query.edit_message_text("↩️ Back to main menu", reply_markup=get_main_buttons())

# === Strategy Logic ===
def majority_strategies_agree(asset: str, expiry: str) -> str:
    # This uses mock logic. Replace with your real strategy combination.
    import random
    return random.choice(["buy", "sell"]) if random.random() > 0.1 else None

# === Signal Dispatcher ===
async def send_signal(context, user_id, asset, expiry):
    decision = majority_strategies_agree(asset, expiry)
    if decision:
        emoji = "🟢" if decision == "buy" else "🔴"
        await context.bot.send_message(
            chat_id=user_id,
            text=f"{emoji} *Signal Alert*\n\n📈 Asset: `{asset}`\n⏰ Expiry: `{expiry}`\n📊 Action: *{decision.upper()}* 🚀",
            parse_mode="Markdown"
        )

# === Auto Interval ===
async def signal_loop():
    while True:
        for uid in list(user_assets):
            if user_states.get(uid):
                await send_signal(app.bot, uid, user_assets[uid], user_expiry.get(uid, "30s"))
        await asyncio.sleep(180)  # every 3 minutes

# === Manual Command ===
async def new_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in user_assets:
        await send_signal(context, uid, user_assets[uid], user_expiry.get(uid, "30s"))

# === Entrypoint ===
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("signal", new_signal))
app.add_handler(CallbackQueryHandler(handle_buttons))

async def run_bot():
    await app.run_polling()

async def run_all():
    start_background_services()
    await asyncio.gather(run_bot(), signal_loop())

if __name__ == "__main__":
    asyncio.run(run_all())
