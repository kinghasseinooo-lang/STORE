 import os
import json
import asyncio
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# ================= إعدادات المطور الأساسية =================
TOKEN = '8674002969:AAHF1WybVzgoTXwg9Qumrxh0PHuEtWxdRbY'  # ضع توكن بوتك هنا
ADMIN_ID = 7481039233          # ضع معرفك (ID) هنا لتفعيل لوحة التحكم
# ==========================================================

DB_FILE = 'database.json'

# دالات إدارة البيانات
def load_db():
    if not os.path.exists(DB_FILE):
        data = {
            "users": [],
            "settings": {
                "channel_id": "@YourChannel", 
                "channel_link": "https://t.me/YourChannel", 
                "force_sub": True
            }
        }
        save_db(data)
        return data
    with open(DB_FILE, 'r', encoding='utf-8') as f: return json.load(f)

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)

# التحقق من الاشتراك
async def is_subscribed(context, user_id):
    db = load_db()
    if not db['settings']['force_sub']: return True
    try:
        member = await context.bot.get_chat_member(chat_id=db['settings']['channel_id'], user_id=user_id)
        return member.status in ['creator', 'administrator', 'member']
    except: return False

# أمر البدء /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db = load_db()
    
    # حفظ المستخدم الجديد
    if user_id not in db['users']:
        db['users'].append(user_id)
        save_db(db)

    # إذا كان المستخدم هو المطور
    if user_id == ADMIN_ID:
        keyboard = [
            [InlineKeyboardButton("📊 الإحصائيات", callback_data="stats"), InlineKeyboardButton("📢 إذاعة", callback_data="broadcast")],
            [InlineKeyboardButton("⚙️ إعدادات القناة", callback_data="set_chan")],
            [InlineKeyboardButton(f"الاشتراك الإجباري: {'✅' if db['settings']['force_sub'] else '❌'}", callback_data="toggle_sub")]
        ]
        await update.message.reply_text(
            f"🛠 **لوحة تحكم المطور**\n\nالقناة الحالية: {db['settings']['channel_id']}\nحالة الاشتراك: {'مفعل ✅' if db['settings']['force_sub'] else 'معطل ❌'}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # فحص الاشتراك للمستخدم العادي
    if not await is_subscribed(context, user_id):
        keyboard = [[InlineKeyboardButton("اضغط هنا للاشتراك 📢", url=db['settings']['channel_link'])],
                    [InlineKeyboardButton("تم الاشتراك ✅", callback_data="check_me")]]
        await update.message.reply_text("عذراً! يجب عليك الاشتراك في القناة أولاً لاستخدام البوت.", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text("أهلاً بك! أرسل لي رابط فيديو تيك توك وسأقوم بتحميله لك فوراً. 📥")

# معالجة الأزرار
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db = load_db()
    user_id = query.from_user.id

    if user_id != ADMIN_ID and query.data != "check_me": return

    if query.data == "stats":
        await query.message.reply_text(f"👤 عدد مستخدمي البوت: {len(db['users'])}")

    elif query.data == "toggle_sub":
        db['settings']['force_sub'] = not db['settings']['force_sub']
        save_db(db)
        await query.message.reply_text(f"تم تغيير حالة الاشتراك إلى: {'مفعل ✅' if db['settings']['force_sub'] else 'معطل ❌'}")

    elif query.data == "broadcast":
        context.user_data['state'] = 'BC'
        await query.message.reply_text("أرسل الآن الرسالة (نص فقط) التي تريد إذاعتها لجميع المستخدمين:")

    elif query.data == "set_chan":
        context.user_data['state'] = 'SET'
        await query.message.reply_text("أرسل معرف القناة الجديد ثم الرابط (بينهما مسافة).\nمثال:\n@MyChannel https://t.me/MyChannel")

    elif query.data == "check_me":
        if await is_subscribed(context, user_id):
            await query.edit_message_text("✅ تم التحقق بنجاح! يمكنك الآن إرسال روابط تيك توك.")
        else:
            await query.answer("أنت غير مشترك في القناة بعد! ❌", show_alert=True)

# معالجة الرسائل (تحميل + إعدادات المطور)
async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    db = load_db()
    state = context.user_data.get('state')

    # إعدادات المطور
    if user_id == ADMIN_ID and state == 'BC':
        count = 0
        for u in db['users']:
            try:
                await context.bot.send_message(chat_id=u, text=text)
                count += 1
            except: continue
        await update.message.reply_text(f"✅ تمت الإذاعة لـ {count} مستخدم.")
        context.user_data['state'] = None
        return

    if user_id == ADMIN_ID and state == 'SET':
        try:
            cid, clink = text.split()
            db['settings']['channel_id'], db['settings']['channel_link'] = cid, clink
            save_db(db)
            await update.message.reply_text("✅ تم تحديث بيانات القناة.")
        except: await update.message.reply_text("❌ خطأ! التنسيق: @المعرف الرابط")
        context.user_data['state'] = None
        return

    # نظام التحميل
    if "tiktok.com" in text:
        if not await is_subscribed(context, user_id):
            await update.message.reply_text("يجب الاشتراك في القناة أولاً!")
            return

        msg = await update.message.reply_text("جاري التحميل... 📥")
        try:
            if not os.path.exists('downloads'): os.makedirs('downloads')
            opts = {'format': 'best', 'outtmpl': 'downloads/%(id)s.%(ext)s', 'quiet': True}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(text, download=True)
                file = ydl.prepare_filename(info)
            with open(file, 'rb') as v:
                await update.message.reply_video(video=v, caption="تم التحميل بواسطة بوتك ✅")
            os.remove(file)
            await msg.delete()
        except Exception as e:
            await msg.edit_text(f"❌ خطأ في التحميل: {str(e)}")

# تشغيل البوت
if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    print("البوت يعمل الآن بكامل الصلاحيات...")
    app.run_polling()
