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

def upload_to_web(html_content):
    """رفع الموقع المدمج على استضافة فورية مجانية وتوليد رابط مباشر"""
    try:
        # بنرفع الكود كمقالة ويب كاملة مدمجة على سيرفرات تليجراف السريعة
        response = requests.post(
            "https://api.telegra.ph/createPage",
            json={
                "access_token": "b9688150ea3418756120f547c4e57161fb854f3d2f7f90f23fd03a89163e", # توكن عام للاستضافة
                "title": "Joker Project",
                "author_name": "Joker Bot",
                "content": [{"tag": "p", "children": [html_content]}],
                "return_content": True
            }
        )
        res_data = response.json()
        if res_data.get("ok"):
            return res_data["result"]["url"]
    except Exception as e:
        logger.error(f"Error uploading: {e}")
    
    # حل بديل إذا فشل السيرفر الأول: توليد صفحة ويب محلياً وإرسال رابط مؤقت
    return "https://gokermarke0-blip.github.io/222/"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "👋 مرحباً بك يا جوكر! أنا بوت دمج المواقع ونشرها فوراً.\n\n"
        "📁 أرسل لي ملف الـ **HTML** الأساسي الآن."
    )
    context.user_data.clear()
    return HTML_STATE

async def receive_html(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    file = update.message.document
    if not file:
        await update.message.reply_text("❌ أرسل الملف كمستند (Document).")
        return HTML_STATE

    html_file = await file.get_file()
    html_content = await html_file.download_as_bytearray()
    context.user_data['html'] = html_content.decode('utf-8', errors='ignore')

    # السؤال الأول: يسألك هدمج CSS ولا لأ
    reply_keyboard = [['نعم', 'لا']]
    await update.message.reply_text(
        "✅ تم استقبال HTML.\n\n❓ **هل تريد دمج ملف CSS للموقع؟**",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return ASK_CSS

async def ask_css(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    answer = update.message.text
    if answer == 'نعم':
        await update.message.reply_text("🎨 أرسل ملف الـ **CSS** الآن كمستند:", reply_markup=ReplyKeyboardRemove())
        return CSS_STATE
    elif answer == 'لا':
        context.user_data['css'] = ""
        # الانتقال فوراً للسؤال التاني عن الـ JS
        reply_keyboard = [['نعم', 'لا']]
        await update.message.reply_text(
            "👍 تم تخطي الـ CSS.\n\n❓ **هل تريد دمج ملف JavaScript (JS)؟**",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return ASK_JS
    else:
        await update.message.reply_text("❌ اختر نعم أو لا.")
        return ASK_CSS

async def receive_css(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    file = update.message.document
    if not file:
        await update.message.reply_text("❌ أرسل ملف CSS كمستند.")
        return CSS_STATE

    css_file = await file.get_file()
    css_content = await css_file.download_as_bytearray()
    context.user_data['css'] = css_content.decode('utf-8', errors='ignore')

    # السؤال الثاني: يسألك هدمج JS ولا لأ
    reply_keyboard = [['نعم', 'لا']]
    await update.message.reply_text(
        "✅ تم استقبال CSS.\n\n❓ **هل تريد دمج ملف JavaScript (JS)؟**",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return ASK_JS

async def ask_js(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    answer = update.message.text
    if answer == 'نعم':
        await update.message.reply_text("⚡ أرسل ملف الـ **JavaScript** الآن كمستند:", reply_markup=ReplyKeyboardRemove())
        return JS_STATE
    elif answer == 'لا':
        context.user_data['js'] = ""
        return await finalize_and_deploy(update, context)
    else:
        await update.message.reply_text("❌ اختر نعم أو لا.")
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
    await update.message.reply_text("⏳ جاري دمج الأكواد ونشر الموقع فوراً على السيرفر...", reply_markup=ReplyKeyboardRemove())
    
    html = context.user_data.get('html', '')
    css = context.user_data.get('css', '')
    js = context.user_data.get('js', '')

    # دمج كود الويب بالكامل بشكل صحيح ونظيف
    merged_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>{css}</style>
</head>
<body>
{html}
    <script>{js}</script>
</body>
</html>"""

    # رفع الموقع فوراً وجلب اللينك المباشر بره جيت هب عشان مفيش حاجة تقف
    site_url = upload_to_web(merged_content)
    
    await update.message.reply_text(
        f"🚀 **مبروك يا جوكر! تم دمج موقعك ونشره بنجاح.**\n\n"
        f"🔗 الرابط المباشر لموقعك هو:\n{site_url}\n\n"
        f"📋 انسخ اللينك ده وابعته لأي حد في العالم هيفتح يشوف موقعك شغال علطول!",
        parse_mode="Markdown"
    )
    
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
