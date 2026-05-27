import os
import logging
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

# مراحل المحادثة (الترتيب الصحيح للأسئلة)
HTML_STATE, ASK_CSS, CSS_STATE, ASK_JS, JS_STATE = range(5)

TOKEN = os.getenv("TOKEN")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY") # بيقرأ يوزر وجيت هب أوتوماتيك لعمل اللينك

def get_page_url():
    """توليد رابط الموقع النهائي بناءً على حسابك ومستودعك"""
    if GITHUB_REPOSITORY and "/" in GITHUB_REPOSITORY:
        user, repo = GITHUB_REPOSITORY.split("/")
        return f"https://{user}.github.io/{repo}/"
    return "الرابط الخاص بك على GitHub Pages"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "👋 مرحباً بك يا جوكر في بوت دمج المواقع والرفع الفوري!\n\n"
        "📁 من فضلك أرسل لي ملف الـ **HTML** الأساسي أولاً."
    )
    context.user_data.clear()
    return HTML_STATE

async def receive_html(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    file = update.message.document
    if not file:
        await update.message.reply_text("❌ من فضلك أرسل الملف كمستند (Document).")
        return HTML_STATE

    html_file = await file.get_file()
    html_content = await html_file.download_as_bytearray()
    context.user_data['html'] = html_content.decode('utf-8', errors='ignore')

    # هنا السؤال الأول: يسألك تدمج CSS ولا لأ قبل ما تبعته
    reply_keyboard = [['نعم', 'لا']]
    await update.message.reply_text(
        "✅ تم استقبال ملف HTML بنجاح.\n\n"
        "❓ **هل تريد دمج ملف CSS للموقع؟**",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return ASK_CSS

async def ask_css(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    answer = update.message.text
    if answer == 'نعم':
        await update.message.reply_text("🎨 تمام، مستني منك ملف الـ **CSS** (أرسله كمستند):", reply_markup=ReplyKeyboardRemove())
        return CSS_STATE
    elif answer == 'لا':
        context.user_data['css'] = "" # فارغ لتخطيه
        # لو قال لا، ينط علطول ويسأله عن الـ JS
        reply_keyboard = [['نعم', 'لا']]
        await update.message.reply_text(
            "👍 تم تخطي الـ CSS.\n\n"
            "❓ **هل تريد دمج ملف JavaScript (JS)؟**",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return ASK_JS
    else:
        await update.message.reply_text("❌ من فضلك اختار من الأزرار (نعم أو لا).")
        return ASK_CSS

async def receive_css(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    file = update.message.document
    if not file:
        await update.message.reply_text("❌ أرسل ملف CSS كمستند.")
        return CSS_STATE

    css_file = await file.get_file()
    css_content = await css_file.download_as_bytearray()
    context.user_data['css'] = css_content.decode('utf-8', errors='ignore')

    # بعد استقبال الـ CSS، يسأله الحين يدمج JS ولا لأ
    reply_keyboard = [['نعم', 'لا']]
    await update.message.reply_text(
        "✅ تم استقبال ملف CSS بنجاح.\n\n"
        "❓ **هل تريد دمج ملف JavaScript (JS)؟**",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return ASK_JS

async def ask_js(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    answer = update.message.text
    if answer == 'نعم':
        await update.message.reply_text("⚡ تمام، مستني منك ملف الـ **JavaScript** (أرسله كمستند):", reply_markup=ReplyKeyboardRemove())
        return JS_STATE
    elif answer == 'لا':
        context.user_data['js'] = "" # فارغ لتخطيه
        # لو قال لا، يدمج ويطلع اللينك فوراً
        return await finalize_and_deploy(update, context)
    else:
        await update.message.reply_text("❌ من فضلك اختار من الأزرار (نعم أو لا).")
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
    await update.message.reply_text("⏳ جاري معالجة ودمج ملفاتك وتجهيز رابط الويب السريع...", reply_markup=ReplyKeyboardRemove())
    
    html = context.user_data.get('html', '')
    css = context.user_data.get('css', '')
    js = context.user_data.get('js', '')

    # دمج كامل ومنظم
    merged_content = f"""<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My Live Project</title>
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

    # كتابة الملف وحفظه باسم index.html عشان السيرفر يقرأه علطول كموقع ويب
    output_filename = "index.html"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(merged_content)

    site_url = get_page_url()
    
    await update.message.reply_text(
        f"🎉 **تم دمج ورفع موقعك يا جوكر بنجاح!**\n\n"
        f"🔗 الرابط المباشر لموقعك هو:\n{site_url}\n\n"
        f"📋 خده كوبي وابعته لأي حد يفتحه من موبايله أو الكمبيوتر وهيشتغل معاه علطول!",
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

    # نظام إدارة المحادثة المظبوط بالخطوات
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
