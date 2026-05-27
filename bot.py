import os
import logging
import requests
import base64
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

HTML_STATE, ASK_CSS, CSS_STATE, ASK_JS, JS_STATE = range(5)

TOKEN = os.getenv("TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")  # بيجيب تلقائياً اسم حسابك/المستودع (مثال: gokermarke0-blip/222)

def get_page_url():
    if GITHUB_REPOSITORY and "/" in GITHUB_REPOSITORY:
        user, repo = GITHUB_REPOSITORY.split("/")
        return f"https://{user}.github.io/{repo}/"
    return "https://gokermarke0-blip.github.io/222/"

def upload_to_github_api(content, filename="index.html"):
    if not GITHUB_REPOSITORY or not GITHUB_TOKEN:
        logger.error("❌ عذراً: GITHUB_TOKEN أو GITHUB_REPOSITORY مش مقروءين في السيرفر.")
        return False
        
    url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/contents/{filename}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # محاولة جلب الـ sha للملف لو كان موجود مسبقاً للتحديث عليه
    sha = None
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            sha = res.json().get("sha")
    except Exception as e:
        logger.error(f"Error getting file SHA: {e}")
        
    content_bytes = content.encode("utf-8")
    content_base64 = base64.b64encode(content_bytes).decode("utf-8")
    
    data = {
        "message": "⚡ المطور جوكر: تحديث الـ index.html عبر البوت",
        "content": content_base64,
        "branch": "main"
    }
    if sha:
        data["sha"] = sha

    try:
        put_res = requests.put(url, headers=headers, json=data)
        if put_res.status_code in [200, 201]:
            logger.info("✅ تم رفع وتحديث الموقع بنجاح!")
            return True
        else:
            logger.error(f"❌ جيت هب رفض الرفع. السبب: {put_res.text}")
            return False
    except Exception as e:
        logger.error(f"حدث خطأ أثناء الاتصال بالـ API: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "👋 مرحباً بك يا جوكر! أنا بوت دمج المواقع ونشرها فوراً.\n\n"
        "📁 أرسل لي ملف الـ **HTML** الأساسي الآن (Document)."
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

    reply_keyboard = [['نعم', 'لا']]
    await update.message.reply_text(
        "✅ تم استقبال HTML بنجاح.\n\n❓ **هل تريد دمج ملف CSS للموقع؟**",
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

    reply_keyboard = [['نعم', 'لا']]
    await update.message.reply_text(
        "✅ تم استقبال CSS بنجاح.\n\n❓ **هل تريد دمج ملف JavaScript (JS)؟**",
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
    await update.message.reply_text("⏳ جاري دمج الأكواد وتحديث موقعك على جيت هب صفحات...", reply_markup=ReplyKeyboardRemove())
    
    html = context.user_data.get('html', '')
    css = context.user_data.get('css', '')
    js = context.user_data.get('js', '')

    merged_content = f"""<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Joker Live Project</title>
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

    success = upload_to_github_api(merged_content, "index.html")
    site_url = get_page_url()
    
    if success:
        await update.message.reply_text(
            f"🚀 **يا جوكر تم دمج أكوادك وتحديث الموقع بنجاح!**\n\n"
            f"🔗 الرابط المباشر لموقعك هو:\n{site_url}\n\n"
            f"📋 افتحه دلوقتي وهتلاقي تصميمك الجديد اشتغل علطول وجاب الملف الصح!",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ جيت هب رفض الرفع. يرجى التأكد من تفعيل صلاحيات (Read and Write permissions) من إعدادات Actions -> General في المستودع.")
        
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ تم إلغاء العملية.", reply_markup=ReplyKeyboardRemove())
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
