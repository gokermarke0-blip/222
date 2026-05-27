import os
import logging
from git import Repo
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
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY") # بيقرأ اسم حسابك والمستودع تلقائياً

def get_page_url():
    """توليد رابط الموقع النهائي"""
    if GITHUB_REPOSITORY and "/" in GITHUB_REPOSITORY:
        user, repo = GITHUB_REPOSITORY.split("/")
        return f"https://{user}.github.io/{repo}/"
    return "https://gokermarke0-blip.github.io/222/"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "👋 مرحباً بك يا جوكر! أنا بوت دمج المواقع ونشرها فوراً.\n\n"
        "📁 أرسل لي ملف الـ **HTML** الأساسي الآن (كمستند Document)."
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

    # السؤال الأول
    reply_keyboard = [['نعم', 'لا']]
    await update.message.reply_text(
        "✅ تم استقبال HTML.\n\n❓ **هل تريد دمج ملف CSS؟**",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return ASK_CSS

async def ask_css(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    answer = update.message.text
    if answer == 'نعم':
        await update.message.reply_text("🎨 أرسل ملف الـ **CSS** الآن (كمستند):", reply_markup=ReplyKeyboardRemove())
        return CSS_STATE
    elif answer == 'لا':
        context.user_data['css'] = ""
        reply_keyboard = [['نعم', 'لا']]
        await update.message.reply_text(
            "👍 تخطينا الـ CSS.\n\n❓ **هل تريد دمج ملف JavaScript؟**",
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

    # السؤال الثاني
    reply_keyboard = [['نعم', 'لا']]
    await update.message.reply_text(
        "✅ تم استقبال CSS.\n\n❓ **هل تريد دمج ملف JavaScript؟**",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return ASK_JS

async def ask_js(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    answer = update.message.text
    if answer == 'نعم':
        await update.message.reply_text("⚡ أرسل ملف الـ **JavaScript** الآن (كمستند):", reply_markup=ReplyKeyboardRemove())
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
    await update.message.reply_text("⏳ جاري دمج الأكواد وتحديث الموقع على جيت هب، ثواني...", reply_markup=ReplyKeyboardRemove())
    
    html = context.user_data.get('html', '')
    css = context.user_data.get('css', '')
    js = context.user_data.get('js', '')

    merged_content = f"""<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>جوكر بروجكت</title>
    <style>{css}</style>
</head>
<body>
{html}
    <script>{js}</script>
</body>
</html>"""

    # كتابة الملف في المستودع الحالي للسيرفر
    output_filename = "index.html"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(merged_content)

    # 🚀 الجزء السحري: البوت بيعمل Commit و Push للموقع الجديد أوتوماتيك لجيت هب
    try:
        repo = Repo(".")
        repo.git.add(output_filename)
        repo.index.commit("Update index.html via Telegram Bot")
        origin = repo.remote(name='origin')
        
        # استخدام التوكن الافتراضي للسيرفر عشان يرفع بدون مشاكل صلاحيات
        github_token = os.getenv("GITHUB_TOKEN")
        if github_token and GITHUB_REPOSITORY:
            remote_url = f"https://x-access-token:{github_token}@github.com/{GITHUB_REPOSITORY}.git"
            origin.set_url(remote_url)
            
        origin.push()
        logger.info("✅ تم عمل Push للملف بنجاح على جيت هب!")
    except Exception as e:
        logger.error(f"❌ فشل الرفع التلقائي: {e}")

    site_url = get_page_url()
    
    await update.message.reply_text(
        f"🚀 **عاش يا جوكر! تم دمج ونشر موقعك بنجاح.**\n\n"
        f"🔗 اللينك المباشر لموقعك هو:\n{site_url}\n\n"
        f"📋 ابعته لأي حد في العالم وهيفتح يشوف موقعك علطول! (لو ما فتحش في أول دقيقة، انتظر ثواني عشان جيت هب يحدث السيرفر).",
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
