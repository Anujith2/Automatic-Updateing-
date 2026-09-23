import logging
import os
import re
import sqlite3
from urllib.parse import quote
from flask import Flask
from threading import Thread
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    ConversationHandler,
    filters
)

# ലോഗിങ് സെറ്റ് ചെയ്യുക
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# കോൺവെർസേഷൻ സ്റ്റേറ്റുകൾ (Setup States)
GET_UPDATE_CHANNEL, GET_DB_CHANNEL, GET_TARGET_LINK, GET_FILE_FORMAT, GET_PHOTO_URL, GET_TOP_HEADING = range(6)

# --- SQLITE DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('bot_configs.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS configs (
            user_id INTEGER PRIMARY KEY,
            update_channel TEXT,
            db_channel INTEGER,
            target_link TEXT,
            file_format TEXT,
            photo_url TEXT,
            top_heading TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def save_user_config(user_id, update_channel, db_channel, target_link, file_format, photo_url, top_heading):
    conn = sqlite3.connect('bot_configs.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO configs (user_id, update_channel, db_channel, target_link, file_format, photo_url, top_heading)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, update_channel, db_channel, target_link, file_format, photo_url, top_heading))
    conn.commit()
    conn.close()

def get_config_by_db(db_channel):
    conn = sqlite3.connect('bot_configs.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, update_channel, target_link, file_format, photo_url, top_heading FROM configs WHERE db_channel = ?', (db_channel,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0], row[1], row[2], row[3], row[4], row[5]
    return None
# -----------------------------

# --- FLASK SERVER ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running successfully and Alive! 🚀"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()
# --------------------

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        payload = context.args[0]
        if payload.startswith("getfile-"):
            await update.message.reply_text(f"📥 You requested file details: {payload}\n\nFile delivery processing...")
            return

    welcome_text = "Hi, I am an automatically update bot"
    
    keyboard = [
        [InlineKeyboardButton("⚙️ Setup My Channels", callback_data="setup_channels")],
        [InlineKeyboardButton("❓ Help & Instructions", callback_data="help_menu")],
        [InlineKeyboardButton("👤 Contact Owner", url="https://t.me/Anujith1238")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def admins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_text = (
        "👑 <b>Admin Information</b>\n\n"
        "If you need any support or want to contact the admin, please reach out to:\n"
        "💬 <b>Contact:</b> @Anujith1238"
    )
    keyboard = [[InlineKeyboardButton("👤 Chat with Admin", url="https://t.me/Anujith1238")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(admin_text, reply_markup=reply_markup, parse_mode="HTML")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🤖 <b>Bot Help & Instructions Menu</b>\n\n"
        "How to use this bot:\n"
        "1️⃣ First, send your <b>Updates Channel ID</b> or Username.\n"
        "2️⃣ Second, send your <b>Database Channel ID</b>.\n"
        "3️⃣ Third, send your target link/ID for the Get File button.\n"
        "4️⃣ Fourth, select your preferred <b>File Format</b> (Text, Video, or Photo Format).\n"
        "5️⃣ Fifth, send your banner Photo URL (if Photo format selected).\n"
        "6️⃣ Finally, send your custom <b>Top Heading</b> text.\n\n"
        "💬 <b>Contact Owner:</b> @Anujith1238"
    )
    keyboard = [[InlineKeyboardButton("👤 Contact Owner", url="https://t.me/Anujith1238")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(help_text, reply_markup=reply_markup, parse_mode="HTML")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "setup_channels":
        await query.message.edit_text(
            "⚙️ <b>Channel Setup Wizard</b>\n\n"
            "1️⃣ Please send your <b>Updates Channel ID</b> or Username (e.g., <code>-100xxxxxxxxxx</code> or <code>@yourchannel</code>):",
            parse_mode="HTML"
        )
        return GET_UPDATE_CHANNEL

    elif query.data == "help_menu":
        help_text = (
            "🤖 <b>Bot Help & Instructions Menu</b>\n\n"
            "Follow the setup wizard steps to configure your channels and photo formats easily.\n\n"
            "💬 <b>Contact Owner:</b> @Anujith1238"
        )
        keyboard = [
            [InlineKeyboardButton("👤 Contact Owner", url="https://t.me/Anujith1238")],
            [InlineKeyboardButton("« Back", callback_data="back_home")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(help_text, reply_markup=reply_markup, parse_mode="HTML")

    elif query.data == "back_home":
        welcome_text = "Hi, I am an automatically update bot"
        keyboard = [
            [InlineKeyboardButton("⚙️ Setup My Channels", callback_data="setup_channels")],
            [InlineKeyboardButton("❓ Help & Instructions", callback_data="help_menu")],
            [InlineKeyboardButton("👤 Contact Owner", url="https://t.me/Anujith1238")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(welcome_text, reply_markup=reply_markup)

async def get_update_channel_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_input = update.message.text.strip()
    try:
        if text_input.startswith("@") or text_input.startswith("https://"):
            update_chat_id = text_input
        else:
            update_chat_id = str(int(text_input))
            
        context.user_data['temp_update_channel'] = update_chat_id
        
        await update.message.reply_text(
            "✅ Updates Channel saved successfully!\n\n"
            "2️⃣ Now, please send your <b>Database Channel ID</b> (e.g., <code>-100xxxxxxxxxx</code>):",
            parse_mode="HTML"
        )
        return GET_DB_CHANNEL
    except Exception as e:
        await update.message.reply_text(f"❌ Invalid format: {e}\nPlease send a valid Channel ID or Username:")
        return GET_UPDATE_CHANNEL

async def get_db_channel_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        db_chat_id = int(update.message.text.strip())
        context.user_data['temp_db_channel'] = db_chat_id
        
        await update.message.reply_text(
            "✅ Database Channel ID saved successfully!\n\n"
            "3️⃣ Now, send your target link/ID for the Get File button:",
            parse_mode="HTML"
        )
        return GET_TARGET_LINK
    except ValueError:
        await update.message.reply_text("❌ Invalid ID! Please send a valid numeric Database Channel ID:")
        return GET_DB_CHANNEL

async def get_target_link_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_link_input = update.message.text.strip()
    context.user_data['temp_target_link'] = target_link_input

    keyboard = [
        [InlineKeyboardButton("📄 Text Format", callback_data="fmt_text")],
        [InlineKeyboardButton("🎬 Video Format", callback_data="fmt_video")],
        [InlineKeyboardButton("🖼️ Photo Format (Banner + Details)", callback_data="fmt_photo")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "✅ Target Link/ID saved successfully!\n\n"
        "4️⃣ Please select your preferred <b>File Format</b>:",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    return GET_FILE_FORMAT

async def get_file_format_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    format_choice = "Text"
    if query.data == "fmt_video":
        format_choice = "Video"
    elif query.data == "fmt_photo":
        format_choice = "Photo"

    context.user_data['temp_file_format'] = format_choice

    if format_choice == "Photo":
        await query.message.edit_text(
            "✅ Photo Format selected!\n\n"
            "5️⃣ Please send the <b>Banner Image URL</b> (ചിത്രത്തിൽ കാണുന്നതുപോലെയുള്ള ലോഗോ/ബാനർ ഇമേജിന്റെ Direct Image Link അയക്കുക):",
            parse_mode="HTML"
        )
        return GET_PHOTO_URL
    else:
        context.user_data['temp_photo_url'] = ""
        await query.message.edit_text(
            "✅ File Format saved successfully!\n\n"
            "6️⃣ Finally, please type and send your custom <b>Top Heading</b> text:",
            parse_mode="HTML"
        )
        return GET_TOP_HEADING

async def get_photo_url_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_url = update.message.text.strip()
    context.user_data['temp_photo_url'] = photo_url

    await update.message.reply_text(
        "✅ Banner Image URL saved successfully!\n\n"
        "6️⃣ Finally, please type and send your custom <b>Top Heading</b> text (e.g., <code>🍁Anujith Allu TV Serials🍁</code>):",
        parse_mode="HTML"
    )
    return GET_TOP_HEADING

async def get_top_heading_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    top_heading = update.message.text.strip()

    update_channel = context.user_data.get('temp_update_channel')
    db_channel = context.user_data.get('temp_db_channel')
    target_link = context.user_data.get('temp_target_link')
    file_format = context.user_data.get('temp_file_format')
    photo_url = context.user_data.get('temp_photo_url', '')

    save_user_config(user_id, update_channel, db_channel, target_link, file_format, photo_url, top_heading)

    success_msg = (
        "🎉 <b>Setup Successful!</b>\n\n"
        f"📢 <b>Updates Channel:</b> <code>{update_channel}</code>\n"
        f"📁 <b>Database Channel:</b> <code>{db_channel}</code>\n"
        f"⚙️ <b>File Format:</b> <code>{file_format}</code>\n"
        f"🏷 <b>Top Heading:</b> {top_heading}\n\n"
        "Your bot is now fully configured!"
    )

    keyboard = [[InlineKeyboardButton("⚙️ Setup Again", callback_data="setup_channels")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(success_msg, reply_markup=reply_markup, parse_mode="HTML")
    return ConversationHandler.END

async def cancel_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Setup cancelled.")
    return ConversationHandler.END

async def auto_post_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post or update.message
    if not message:
        return

    incoming_chat_id = message.chat.id
    config = get_config_by_db(incoming_chat_id)
    if not config:
        return

    user_id, target_update_channel, target_link, file_format, photo_url, top_heading = config

    file_name = ""
    if message.document:
        file_name = message.document.file_name
    elif message.video:
        file_name = message.video.file_name or message.caption or "Unknown Video"
    elif message.caption:
        file_name = message.caption

    if not file_name:
        return

    clean_name = file_name.replace("_", " ").replace(".", " ")
    
    season_match = re.search(r's0?(\d+)', clean_name, re.IGNORECASE)
    season = season_match.group(1) if season_match else "01"
    
    ep_match = re.search(r'(?:ep?|episode)\s*([\d\-]+)', clean_name, re.IGNORECASE)
    if ep_match:
        episode = ep_match.group(1)
    else:
        num_match = re.findall(r'\b(?:ep?|episode)?\s*(\d{1,4})\b', clean_name, re.IGNORECASE)
        episode = num_match[-1] if num_match else "01"

    quality_match = re.search(r'(480p|576p|720p|1080p)', clean_name, re.IGNORECASE)
    quality = quality_match.group(1) if quality_match else "720p"

    title_part_match = re.split(r'(?:s0?\d+|ep?\s*\d+|episode|\b480p\b|\b576p\b|\b720p\b|\b1080p\b)', clean_name, flags=re.IGNORECASE)
    base_title = title_part_match[0].strip() if title_part_match else clean_name

    unwanted_words = ['ramesh', 'helps', 'nidhi', 'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec', 'snxt', 'web', 'dl', 'tamil', 'malayalam', 'zee5', 'jiocinema', 'sunnxt', 'manoramamax']
    words = base_title.split()
    filtered_words = [w for w in words if w.lower() not in unwanted_words]
    title_clean = filtered_words[0] if filtered_words else "Serial Video"

    heading_to_show = top_heading if top_heading else "🍁Anujith Allu TV Serials🍁"

    # 'Format' എന്ന ഭാഗം പൂർണ്ണമായി ഒഴിവാക്കി, നിങ്ങൾ ആവശ്യപ്പെട്ട 4 കാര്യങ്ങൾ മാത്രം നൽകിയിരിക്കുന്നു:
    # 1. File Name, 2. Season, 3. Episode, 4. Quality
    caption_text = (
        f"<b>{heading_to_show}</b>\n\n"
        f"📁 <b>File Name :</b> {file_name}\n"
        f"🎞 <b>Season :</b> {season.zfill(2)}\n"
        f"📌 <b>Episode :</b> {episode}\n"
        f"🎬 <b>Quality :</b> {quality}"
    )

    encoded_title = quote(title_clean)
    
    if target_link:
        if target_link.startswith("https://"):
            get_file_url = f"{target_link.rstrip('/')}/{encoded_title}-S{season.zfill(2)}E{episode}"
        elif target_link.startswith("@"):
            get_file_url = f"https://t.me/{target_link.lstrip('@')}"
        elif target_link.startswith("-") or target_link.isdigit():
            chat_id_clean = target_link.lstrip('-')
            if chat_id_clean.startswith("100"):
                get_file_url = f"https://t.me/c/{chat_id_clean[3:]}"
            else:
                get_file_url = f"https://t.me/c/{chat_id_clean}"
        else:
            get_file_url = f"https://t.me/{target_link}"
    else:
        get_file_url = f"https://telegram.me/Anujith1bot?start=getfile-{encoded_title}-S{season.zfill(2)}E{episode}"

    keyboard = [[InlineKeyboardButton("📥 Get File", url=get_file_url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        chat_to_send = int(target_update_channel) if str(target_update_channel).lstrip('-').isdigit() else target_update_channel

        if file_format == "Photo" and photo_url:
            await context.bot.send_photo(
                chat_id=chat_to_send,
                photo=photo_url,
                caption=caption_text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        elif file_format == "Video" and (message.video or message.document):
            await context.bot.copy_message(
                chat_id=chat_to_send,
                from_chat_id=incoming_chat_id,
                message_id=message.message_id,
                caption=caption_text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        else:
            await context.bot.send_message(
                chat_id=chat_to_send,
                text=caption_text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )

        logger.info(f"Auto post sent successfully to channel: {target_update_channel}!")
    except Exception as e:
        logger.error(f"Error sending auto post:[span_1](start_span)[span_1](end_span) {e}")

def main():
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        raise ValueError("❌ TELEGRAM_BOT_TOKEN is missing in Environment Variables!")
    
    keep_alive()
    app = ApplicationBuilder().token(TOKEN).build()

    setup_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^setup_channels$")],
        states={
            GET_UPDATE_CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_update_channel_step)],
            GET_DB_CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_db_channel_step)],
            GET_TARGET_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_target_link_step)],
            GET_FILE_FORMAT: [CallbackQueryHandler(get_file_format_step, pattern="^fmt_")],
            GET_PHOTO_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_photo_url_step)],
            GET_TOP_HEADING: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_top_heading_step)],
        },
        fallbacks=[CommandHandler("cancel", cancel_setup)]
    )

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("admins", admins_command))
    app.add_handler(setup_handler)
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ChatType.CHANNEL & (filters.VIDEO | filters.Document.ALL | filters.TEXT), auto_post_handler))

    print("Bot is running with Photo Format and cleaned caption (without Format field)...")
    app.run_polling()

if __name__ == "__main__":
    main()
