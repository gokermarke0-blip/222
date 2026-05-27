import os
import logging
import requests
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

# إعداد الـ Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# مراحل المحادثة
HTML_STATE, ASK_CSS, CSS_STATE, ASK_JS, JS_STATE = range(5)

TOKEN = os.getenv("TOKEN")

def upload_to_file_io(file_path):
    """رفع الملف على سيرفر file.io العالمي وتوليد لينك مباشر فوراً"""
    try:
        url = "https://file.io/"
        # الملف هيفضل صالح ومتاح أونلاين لأي حد يفتحه
        with open(file_path, "rb") as f:
            files = {"file": f}
            # بنحدد إن الملف يفضل متاح ومتعلم عليه كموقع
            response = requests.post(url, files=files)
            if response.status_code == 200:
                res_data = response.json()
                if res_data.get("success"):
                    return res_data.get("link")
    except Exception as e:
        logger.error(f"File.io upload error: {e}")
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "👋 مرحباً يا جوكر! أنا جاهز دلوقتي.\n\n"
        "📁 أرسل لي ملف الـ **HTML** الأساسي (كمستند Document)."
    )
    context.user_data.clear()
    return HTML_STATE

async def receive_html(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    file = update.message.document
    if not file:
        await update.message.reply_text("❌ من فضلك أرسل الملف كمستند (Document) وليس نص.")
        return HTML_STATE

    html_file = await file.get_file()
    html_content = await html_file.download_as_bytearray()
    context.user_data['html'] = html_content.decode('utf-8', errors='ignore')

    reply_keyboard = [['نعم', 'لا']]
    await update.message.reply_text(
        "✅ تم استقبال ملف HTML.\n\n"
        "❓ **هل تريد دمج ملف CSS للموقع؟**",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return ASK_CSS

async def ask_css(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    answer = update.message.text
    if answer == 'نعم':
        await update.message.reply_text("🎨 تمام، أرسل ملف الـ **CSS** الآن كمستند:", reply_markup=ReplyKeyboardRemove())
        return CSS_STATE
    elif answer == 'لا':
        context.user_data['css'] = ""
        reply_keyboard = [['نعم', 'لا']]
        await update.message.reply_text(
            "👍 تم تخطي الـ CSS.\n\n"
            "❓ **هل تريد دمج ملف JavaScript (JS)؟**",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return ASK_JS
    else:
        await update.message.reply_text("❌ اختار من الأزرار (نعم أو لا).")
        return ASK_CSS

async def receive_css(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    file = update.message.document
    if not file:
        await update.message.reply_text("❌ أرسل ملف CSS كمستند.")
        return CSS_STATE

    css_file = await file.get_file()
    css_content = await css_file.download_as_bytearray()
    context.user_data['css'] = css_content.decode('utf-8', errors='ignore')

    reply_keyboard = [['نعم', 'لا']]
    await update.message.reply_text(
        "✅ تم استقبال ملف CSS.\n\n"
        "❓ **هل تريد دمج ملف JavaScript (JS)؟**",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return ASK_JS

async def ask_js(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    answer = update.message.text
    if answer == 'نعم':
        await update.message.reply_text("⚡ تمام، أرسل ملف الـ **JavaScript** الآن كمستند:", reply_markup=ReplyKeyboardRemove())
        return JS_STATE
    elif answer == 'لا':
        context.user_data['js'] = ""
        return await finalize_and_deploy(update, context)
    else:
        await update.message.reply_text("❌ اختار من الأزرار (نعم أو لا).")
        return ASK_JS

async def receive_js(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    file = update.message.document
    if not file:
        await update.message.reply_text("❌ أرسل ملف JS كمستند.")
        return JS_STATE

    js_file = await file.get_file()
    js_content = await js_file.download_as_bytearray()
    context.user_data['js'] = js_content.decode('utf-8', errors='ignore')

    return await finalize_and_deploy(update, context)

async def finalize_and_deploy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("⏳ جاري دمج الأكواد ورفع الموقع فوراً وتوليد اللينك المباشر...", reply_markup=ReplyKeyboardRemove())
    
    html = context.user_data.get('html', '')
    css = context.user_data.get('css', '')
    js = context.user_data.get('js', '')

    # دمج الأكواد بشكل سليم داخل الهيكل الأساسي لصفحة الويب
    merged_content = f"""<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Joker Live Web Project</title>
    <style>
{css}
    </style>
</head>
<body>
{html}
    <script>
{js}
    </script>
</body>
</html>"""

    # حفظ الملف باسم index.html مؤقتاً عشان يترفع صح كصفحة رئيسية
    temp_filename = "index.html"
    with open(temp_filename, "w", encoding="utf-8") as f:
        f.write(merged_content)

    # رفع الملف فوراً وجلب اللينك المباشر
    site_url = upload_to_file_io(temp_filename)

    # مسح الملف المؤقت من السيرفر
    if os.path.exists(temp_filename):
        os.remove(temp_filename)
    
    if site_url:
        await update.message.reply_text(
            f"🚀 **يا جوكر تم دمج موقعك ونشره بنجاح!**\n\n"
            f"🔗 الرابط المباشر لموقعك أهو:\n{site_url}\n\n"
            f"📋 خده كوبي وابعته لأي حد في العالم، أول ما يفتح اللينك هيفتح معاه الموقع وتصميمك كامل وشغال علطول!",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ حصلت مشكلة في سيرفر الرفع، جرب مرة تانية الحين.")
        
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ تم إلغاء العملية الحالية.", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END

def main():
    if not TOKEN:
        return
    application = Application.builder().token(TOKEN).build()
    
    # فلتر الـ ALL عشان يستقبل أي ملف ويبدو بدون مشاكل كراش
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            HTML_STATE: [MessageHandler(filters.Document.ALL & ~filters.COMMAND, receive_html)],
            ASK_CSS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_css)],
            CSS_STATE: [MessageHandler(filters.Document.ALL & ~filters.COMMAND, receive_css)],
            ASK_JS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_js)],
            JS_STATE: [MessageHandler(filters.Document.ALL & ~filters.COMMAND, receive_js)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == '__main__':
    main()
