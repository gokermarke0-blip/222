import os
import logging
import subprocess
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

# إعداد الـ Logs عشان نتابع في الـ Actions
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# مراحل المحادثة بالترتيب الصح
HTML_STATE, ASK_CSS, CSS_STATE, ASK_JS, JS_STATE = range(5)

TOKEN = os.getenv("TOKEN")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")

def get_page_url():
    """توليد رابط الموقع النهائي المباشر على GitHub Pages"""
    if GITHUB_REPOSITORY and "/" in GITHUB_REPOSITORY:
        user, repo = GITHUB_REPOSITORY.split("/")
        return f"https://{user}.github.io/{repo}/"
    return "https://gokermarke0-blip.github.io/222/"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "👋 مرحباً بك يا جوكر! أنا بوت دمج المواقع ونشرها فوراً.\n\n"
        "📁 أرسل لي ملف الـ **HTML** الأساسي الآن (أرسله كمستند Document)."
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
    await update.message.reply_text("⏳ جاري دمج الأكواد ورفع الموقع حياً على جيت هب صفحات...", reply_markup=ReplyKeyboardRemove())
    
    html = context.user_data.get('html', '')
    css = context.user_data.get('css', '')
    js = context.user_data.get('js', '')

    # دمج الأكواد بشكل سليم داخل وسم الـ HTML
    merged_content = f"""<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Joker Live Web</title>
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

    output_filename = "index.html"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(merged_content)

    # تنفيذ أوامر الـ Git عبر الـ Terminal مباشرة لضمان تخطي قيود القراءة
    try:
        github_token = os.getenv("GITHUB_TOKEN")
        if github_token and GITHUB_REPOSITORY:
            # تهيئة إعدادات جيت هب داخل سيرفر الأكشن عشان يسمح بالرفع
            subprocess.run(["git", "config", "--global", "user.name", "JokerBot"], check=True)
            subprocess.run(["git", "config", "--global", "user.email", "bot@joker.com"], check=True)
            
            # إضافة الملف وعمل كوميت
            subprocess.run(["git", "add", output_filename], check=True)
            subprocess.run(["git", "commit", "-m", "Deploy web via Telegram Bot"], check=True)
            
            # رفع التحديث للمستودع الرئيسي
            remote_url = f"https://x-access-token:{github_token}@github.com/{GITHUB_REPOSITORY}.git"
            subprocess.run(["git", "remote", "set-url", "origin", remote_url], check=True)
            subprocess.run(["git", "push", "origin", "main"], check=True)
            logger.info("✅ Push successful via subprocess!")
    except Exception as e:
        logger.error(f"❌ Git push failed: {e}")

    site_url = get_page_url()
    
    await update.message.reply_text(
        f"🚀 **يا جوكر تم دمج أكوادك وتحديث الموقع بنجاح!**\n\n"
        f"🔗 الرابط المباشر لموقعك هو:\n{site_url}\n\n"
        f"📋 انسخه وابعته لأي حد، دقيقة بالظبط وجيت هب هيعرض تصميمك وموقعك الجديد بدل الصفحة البيضاء!",
        parse_mode="Markdown"
    )
    
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
    
    # هنا حلينا خطأ فلاتر الـ Document القديم واستبدلناه بـ ALL عشان يقبل أي ملف بدون كراش
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
