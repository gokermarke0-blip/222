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

# إعدادات الـ Logs عشان تتابع تشغيل البوت في الـ Actions
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تحديد مراحل المحادثة (Conversation States)
HTML_STATE, CSS_STATE, JS_STATE = range(3)

# الكود بيقرأ التوكن من السيرفر بشكل آمن
TOKEN = os.getenv("TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """بداية تشغيل البوت والترحيب بالمستخدم"""
    await update.message.reply_text(
        "👋 أهلاً بك في بوت دمج ملفات الويب!\n\n"
        "📁 من فضلك أرسل لي ملف الـ **HTML** أولاً.",
        parse_mode="Markdown"
    )
    # تفريغ البيانات السابقة للمستخدم لضمان عدم التداخل
    context.user_data.clear()
    return HTML_STATE

async def receive_html(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """استقبال ملف HTML"""
    file = update.message.document
    
    # التأكد أن الملف مبعوث كـ Document
    if not file:
        await update.message.reply_text("❌ عذراً، يجب إرسال الملف كمستند (Document).")
        return HTML_STATE

    await update.message.reply_text("⏳ جاري تحميل ملف HTML...")
    html_file = await file.get_file()
    html_content = await html_file.download_as_bytearray()
    
    # حفظ المحتوى في ذاكرة المستخدم
    context.user_data['html'] = html_content.decode('utf-8', errors='ignore')
    
    await update.message.reply_text("✅ تم استقبال HTML بنجاح.\n🎨 الآن، أرسل لي ملف الـ **CSS**.")
    return CSS_STATE

async def receive_css(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """استقبال ملف CSS"""
    file = update.message.document
    
    if not file:
        await update.message.reply_text("❌ من فضلك أرسل ملف الـ CSS كمستند.")
        return CSS_STATE

    await update.message.reply_text("⏳ جاري تحميل ملف CSS...")
    css_file = await file.get_file()
    css_content = await css_file.download_as_bytearray()
    
    context.user_data['css'] = css_content.decode('utf-8', errors='ignore')
    
    await update.message.reply_text("✅ تم استقبال CSS بنجاح.\n⚡ أخيرًا، أرسل لي ملف الـ **JavaScript (JS)**.")
    return JS_STATE

async def receive_js(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """استقبال ملف JS، ودمج الملفات وإرسال النتيجة الفورية"""
    file = update.message.document
    
    if not file:
        await update.message.reply_text("❌ من فضلك أرسل ملف الـ JavaScript كمستند.")
        return JS_STATE

    await update.message.reply_text("⏳ جاري تحميل ملف JavaScript وبدء عملية الدمج المباشر...")
    js_file = await file.get_file()
    js_content = await js_file.download_as_bytearray()
    
    context.user_data['js'] = js_content.decode('utf-8', errors='ignore')
    
    # جلب المحتويات المرفوعة مسبقاً من الذاكرة
    html = context.user_data.get('html', '')
    css = context.user_data.get('css', '')
    js = context.user_data.get('js', '')
    
    # عملية الدمج السحرية داخل ملف HTML واحد
    merged_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Merged Project</title>
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

    # كتابة الملف المدمج وحفظه مؤقتاً لإرساله
    output_filename = "index_merged.html"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(merged_html)
        
    # إرسال الملف النهائي للمستخدم
    with open(output_filename, "rb") as f:
        await update.message.reply_document(
            document=f,
            filename="index.html",
            caption="🎉 تم دمج ملفاتك بنجاح في ملف واحد جاهز للتصفح والتشغيل!"
        )
        
    # تنظيف الملفات المؤقتة وبيانات المستخدم بعد الانتهاء
    if os.path.exists(output_filename):
        os.remove(output_filename)
    context.user_data.clear()
    
    await update.message.reply_text("✨ إذا كنت تريد دمج ملفات أخرى، أرسل لي أمر /start من جديد.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """إلغاء العملية الحالية في أي وقت"""
    await update.message.reply_text("❌ تم إلغاء عملية الدمج الحالية.", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END

def main():
    """تشغيل وإعداد البوت"""
    if not TOKEN:
        logger.error("❌ خطأ: لم يتم العثور على متغير TOKEN السرّي في السيرفر!")
        return

    # إنشاء التطبيق وربطه بالتوكن
    application = Application.builder().token(TOKEN).build()

    # إعداد نظام تتبع تسلسل المحادثة والأوامر (الأضمن لمنع أخطاء الـ MimeTypes)
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            HTML_STATE: [MessageHandler(filters.Document.ALL & ~filters.COMMAND, receive_html)],
            CSS_STATE: [MessageHandler(filters.Document.ALL & ~filters.COMMAND, receive_css)],
            JS_STATE: [MessageHandler(filters.Document.ALL & ~filters.COMMAND, receive_js)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    # تشغيل البوت والبدء في استقبال التحديثات
    print("🤖 البوت يعمل الآن بكفاءة من خلال GitHub Actions ومستعد لاستقبال الملفات...")
    application.run_polling()

if __name__ == '__main__':
    main()
