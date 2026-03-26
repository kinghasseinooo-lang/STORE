import os
import asyncio
import yt_dlp
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ضع التوكن الخاص بك هنا
TOKEN = '8674002969:AAHF1WybVzgoTXwg9Qumrxh0PHuEtWxdRbY'

# إعدادات yt-dlp للتحميل من تيك توك
YDL_OPTIONS = {
    'format': 'best',
    'outtmpl': 'downloads/%(id)s.%(ext)s',
    'noplaylist': True,
    'quiet': True,
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً بك! أرسل لي رابط فيديو تيك توك وسأقوم بتحميله لك فوراً.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    
    if "tiktok.com" not in url:
        return # يتجاهل الرسائل التي لا تحتوي على رابط تيك توك

    status_msg = await update.message.reply_text("جاري المعالجة... انتظر قليلاً ⏳")

    try:
        # إنشاء مجلد التحميل إذا لم يكن موجوداً
        if not os.path.exists('downloads'):
            os.makedirs('downloads')

        # التحميل باستخدام yt-dlp
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        # إرسال الفيديو للمستخدم
        with open(filename, 'rb') as video:
            await update.message.reply_video(video=video, caption="تم التحميل بواسطة بوتك الخاص ✅")

        # حذف الملف بعد الإرسال لتوفير المساحة
        os.remove(filename)
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"عذراً، حدث خطأ أثناء التحميل: {str(e)}")

def main():
    # بناء التطبيق
    application = Application.builder().token(TOKEN).build()

    # الأوامر والمستقبلات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("البوت يعمل الآن...")
    application.run_polling()

if __name__ == '__main__':
    main()import os
import json
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# --- الإعدادات الأولية ---
TOKEN = 'YOUR_BOT_TOKEN_HERE'
ADMIN_ID = 123456789  # معرفك الخاص

# ملفات البيانات
DB_FILE = 'users.json'
SETTINGS_FILE = 'settings.json'

# --- دالات إدارة البيانات ---
def get_settings():
    if not os.path.exists(SETTINGS_FILE):
        default = {"channel_id": "@YourChannel", "channel_link": "https://t.me/YourChannel", "force_sub": True}
        with open(SETTINGS_FILE, 'w') as f: json.dump(default, f)
        return default
    with open(SETTINGS_FILE, 'r') as f: return json.load(f)

def save_settings(data):
    with open(SETTINGS_FILE, 'w') as f: json.dump(data, f)

def load_users():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f: return json.load(f)
    return []

# --- التحقق من الاشتراك ---
async def check_sub(context, user_id):
    settings = get_settings()
    if not settings['force_sub']: return True
    try:
        member = await context.bot.get_chat_member(chat_id=settings['channel_id'], user_id=user_id)
        return member.status in ['creator', 'administrator', 'member']
    except: return False

# --- الأوامر ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # حفظ المستخدم
    users = load_users()
    if user_id not in users:
        users.append(user_id)
        with open(DB_FILE, 'w') as f: json.dump(users, f)

    settings = get_settings()
    
    # لوحة التحكم للمطور
    if user_id == ADMIN_ID:
        keyboard = [
            [InlineKeyboardButton("📊 الإحصائيات", callback_data="stats"), InlineKeyboardButton("📢 إذاعة", callback_data="broadcast")],
            [InlineKeyboardButton("📢 إعدادات القناة", callback_data="edit_channel")],
            [InlineKeyboardButton("🔛 تفعيل/تعطيل الاشتراك", callback_data="toggle_sub")]
        ]
        await update.message.reply_text(f"مرحباً مطور! حالة الاشتراك الآن: {'مفعل ✅' if settings['force_sub'] else 'معطل ❌'}", 
                                       reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # فحص الاشتراك للمستخدمين
    if not await check_sub(context, user_id):
        keyboard = [[InlineKeyboardButton("اشترك هنا 📢", url=settings['channel_link'])],
                    [InlineKeyboardButton("تم الاشتراك ✅", callback_data="verify")]]
        await update.message.reply_text("عذراً، اشترك بالقناة أولاً لتتمكن من استخدام البوت!", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text("أهلاً بك! أرسل رابط تيك توك للتحميل.")

# --- معالجة الأزرار ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    settings = get_settings()

    if query.data == "stats":
        await query.message.reply_text(f"عدد المستخدمين: {len(load_users())}")
    
    elif query.data == "toggle_sub":
        settings['force_sub'] = not settings['force_sub']
        save_settings(settings)
        await query.edit_message_text(f"تم تغيير حالة الاشتراك إلى: {'مفعل ✅' if settings['force_sub'] else 'معطل ❌'}")

    elif query.data == "edit_channel":
        context.user_data['action'] = 'set_channel'
        await query.message.reply_text("أرسل معرف القناة الجديد (مع الـ @) ثم مسافة ثم رابط القناة.\nمثال:\n@MyChannel https://t.me/MyChannel")

    elif query.data == "broadcast":
        context.user_data['action'] = 'bc'
        await query.message.reply_text("أرسل نص الإذاعة الآن:")

# --- معالجة الرسائل ---
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    action = context.user_data.get('action')

    # إعدادات القناة من داخل البوت
    if action == 'set_channel' and user_id == ADMIN_ID:
        try:
            parts = text.split()
            settings = get_settings()
            settings['channel_id'] = parts[0]
            settings['channel_link'] = parts[1]
            save_settings(settings)
            await update.message.reply_text("✅ تم تحديث بيانات القناة بنجاح!")
        except:
            await update.message.reply_text("❌ خطأ في التنسيق! تأكد من إرسال المعرف ثم الرابط.")
        context.user_data['action'] = None
        return

    # الإذاعة
    if action == 'bc' and user_id == ADMIN_ID:
        users = load_users()
        for u in users:
            try: await context.bot.send_message(u, text)
            except: continue
        await update.message.reply_text("✅ تم إرسال الإذاعة للجميع.")
        context.user_data['action'] = None
        return

    # التحميل (TikTok)
    if "tiktok.com" in text:
        if not await check_sub(context, user_id):
            await update.message.reply_text("اشترك بالقناة أولاً!")
            return
        # كود التحميل هنا (نفس الكود السابق باستخدام yt-dlp)
        await update.message.reply_text("جاري التحميل... 📥")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.run_polling()

if __name__ == '__main__':
    main()

