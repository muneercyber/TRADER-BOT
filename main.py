# main.py
import asyncio
import json
import os
import subprocess
import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ChatPermissions
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
from playwright.async_api import async_playwright
import nest_asyncio
nest_asyncio.apply()

TOKEN = '7799176242:AAFNZnsgWA7FBR3g2txQADQBR5stDY3cQWM'
ADMIN_ID = 5734178963
ALLOWED_USERS_FILE = 'allowed_users.json'
BRAVE_PATH = "C:\\Users\\escanor\\AppData\\Local\\BraveSoftware\\Brave-Browser\\Application\\brave.exe"
PO_URL = 'https://pocketoption.com/en/cabinet/demo-quick-high-low/'

# Categorized OTC assets
OTC_ASSETS = {
    "Crypto": ["BTCUSD_otc", "ETHUSD_otc", "LTCUSD_otc", "XRPUSD_otc", "BCHUSD_otc",
               "ADAUSD_otc", "BNBUSD_otc", "DOTUSD_otc", "SOLUSD_otc", "DOGEUSD_otc"],
    "Forex": ["EURUSD_otc", "USDJPY_otc", "GBPUSD_otc", "AUDUSD_otc", "USDCHF_otc",
              "USDCAD_otc", "EURJPY_otc", "GBPJPY_otc", "NZDUSD_otc", "EURGBP_otc"],
    "Commodities": ["Gold_otc", "Silver_otc", "Oil_otc", "NaturalGas_otc", "Copper_otc"],
    "Stocks": ["AAPL_otc", "TSLA_otc", "GOOGL_otc", "AMZN_otc", "MSFT_otc"]
}

user_states = {}
last_signal_time = {}

def load_allowed_users():
    if not os.path.exists(ALLOWED_USERS_FILE):
        with open(ALLOWED_USERS_FILE, 'w') as f:
            json.dump([ADMIN_ID, 615643589], f)
    with open(ALLOWED_USERS_FILE) as f:
        return json.load(f)

def save_allowed_users(users):
    with open(ALLOWED_USERS_FILE, 'w') as f:
        json.dump(users, f)

async def launch_browser():
    from playwright.async_api import async_playwright
    auth_path = '.auth'
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=auth_path,
            executable_path=BRAVE_PATH,
            headless=os.path.exists(auth_path)
        )
        page = await browser.new_page()
        await page.goto(PO_URL)
        print("✅ Brave launched and session loaded.")
        if not os.path.exists(auth_path):
            print("🔐 Login manually then close the window.")
            while browser.is_connected():
                await asyncio.sleep(2)

async def send_controls(chat_id, context):
    keyboard = [
        [InlineKeyboardButton("Start", callback_data="start"),
         InlineKeyboardButton("Stop", callback_data="stop")],
        [InlineKeyboardButton("Admin Panel", callback_data="admin")]
    ]
    await context.bot.send_message(chat_id, "📋 Bot Controls:", reply_markup=InlineKeyboardMarkup(keyboard))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in allowed_users:
        await update.message.reply_text("❌ Access Denied.")
        return
    await send_controls(update.effective_chat.id, context)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    await query.answer()

    if uid not in allowed_users:
        return await query.edit_message_text("❌ Access Denied.")

    data = query.data

    if data == "start":
        user_states[uid] = {"running": True}
        await query.edit_message_text("✅ Bot Started.")
        await asset_category_menu(query)
    elif data == "stop":
        user_states[uid] = {"running": False}
        await query.edit_message_text("⛔ Bot Stopped.")
    elif data == "admin":
        await admin_menu(query)
    elif data.startswith("cat:"):
        category = data.split(":")[1]
        await asset_selection_menu(query, category)
    elif data == "back":
        await asset_category_menu(query)
    elif data.startswith("pair:"):
        pair = data.split(":")[1]
        user_states[uid]["pair"] = pair
        await expiry_menu(query)
    elif data.startswith("exp:"):
        expiry = int(data.split(":")[1])
        user_states[uid]["expiry"] = expiry
        await query.edit_message_text(f"✅ Selected {user_states[uid]['pair']} with expiry {expiry}s")
        await run_analysis_and_signal(uid, context)
    elif data == "request":
        await run_analysis_and_signal(uid, context)

async def admin_menu(query):
    keyboard = [
        [InlineKeyboardButton("Add User", callback_data="add_user"),
         InlineKeyboardButton("Remove User", callback_data="remove_user")]
    ]
    await query.edit_message_text("🛠️ Admin Options:", reply_markup=InlineKeyboardMarkup(keyboard))

async def asset_category_menu(query):
    keyboard = [[InlineKeyboardButton(cat, callback_data=f"cat:{cat}")] for cat in OTC_ASSETS]
    await query.edit_message_text("📊 Select Category:", reply_markup=InlineKeyboardMarkup(keyboard))

async def asset_selection_menu(query, category):
    keyboard = [[InlineKeyboardButton(pair, callback_data=f"pair:{pair}")] for pair in OTC_ASSETS[category]]
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back")])
    await query.edit_message_text(f"Select {category} Pair:", reply_markup=InlineKeyboardMarkup(keyboard))

async def expiry_menu(query):
    keyboard = [
        [InlineKeyboardButton("5s", callback_data="exp:5"),
         InlineKeyboardButton("15s", callback_data="exp:15"),
         InlineKeyboardButton("30s", callback_data="exp:30"),
         InlineKeyboardButton("60s", callback_data="exp:60")],
        [InlineKeyboardButton("📩 Request Signal", callback_data="request")]
    ]
    await query.edit_message_text("⏳ Select Expiry Time:", reply_markup=InlineKeyboardMarkup(keyboard))

async def run_analysis_and_signal(uid, context):
    pair = user_states[uid].get("pair")
    expiry = user_states[uid].get("expiry", 60)
    if not pair:
        return
    now = time.time()
    if now - last_signal_time.get(uid, 0) < 180:
        return
    last_signal_time[uid] = now
    # Dummy strategy logic — replace with actual signal logic
    direction = "🔼 BUY" if int(now) % 2 == 0 else "🔽 SELL"
    emoji = "🚀"
    await context.bot.send_message(uid, f"{emoji} *{direction}* on `{pair}`\n⏱ Expiry: {expiry}s",
                                   parse_mode='Markdown')

async def run_po_sniffer():
    while True:
        subprocess.run(["python", "po_sniffer.py"])
        await asyncio.sleep(3)

async def run_bot():
    global allowed_users
    allowed_users = load_allowed_users()
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    print("🚀 Telegram Bot Running...")

async def run_all():
    await asyncio.gather(
        launch_browser(),
        run_bot(),
        run_po_sniffer()
    )

if __name__ == "__main__":
    try:
        asyncio.run(run_all())
    except RuntimeError:
        # Fix already running loop
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run_all())
