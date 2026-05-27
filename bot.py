import os
import io
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

# التوكن من المتغيرات البيئية
TOKEN = os.environ.get("TOKEN", "8877424053:AAEB2wz4_BmLMlcJASFuoMaJ-_6nNOqL_VQ")

# حالات المحادثة
HTML_STATE, CSS_STATE, JS_STATE = range(3)

# تخزين البيانات مؤقتاً في الـ context.user_data بدل الـ dict العام لمنع تداخل بيانات المستخدمين
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear() # تفريغ البيانات القديمة
    await update.message.reply_text(
        "🔰 مرحباً! أنا بوت لدمج ملفات HTML + CSS + JS في ملف واحد.\n\n"
        "📥 أرسل لي ملف **HTML** الآن لتنسيقه:"
    )
    return HTML_STATE

async def receive_html(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document or not document.file_name.endswith('.html'):
        await update.message.reply_text("⚠️ يرجى إرسال ملف HTML صحيح وامتداده `.html`!")
        return HTML_STATE
    
    # الطريقة الصحيحة لتحميل الملف في الإصدارات الحديثة لقراءة محتواه مباشرة في الذاكرة
    tg_file = await document.get_file()
    file_bytes = await tg_file.download_as_bytearray()
    html_content = file_bytes.decode('utf-8')
    
    context.user_data['html'] = html_content
    
    keyboard = [
        [InlineKeyboardButton("✅ نعم، أريد دمج CSS", callback_data="yes_css")],
        [InlineKeyboardButton("❌ لا، تخطى الـ CSS", callback_data="no_css")]
    ]
    await update.message.reply_text(
        "✅ تم استلام ملف HTML بنجاح.\n"
        "⚡ هل تريد دمج ملف CSS معه؟",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CSS_STATE

async def handle_css_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "yes_css":
        await query.message.edit_text("📎 أرسل ملف **CSS** الآن:")
        return CSS_STATE
    else:
        # تخطي الـ CSS والانتقال للـ JS مباشرة
        keyboard = [
            [InlineKeyboardButton("✅ نعم، أريد دمج JS", callback_data="yes_js")],
            [InlineKeyboardButton("❌ لا، ادمج الملفات الآن", callback_data="no_js")]
        ]
        await query.message.edit_text(
            "👍 تم تخطي CSS.\n"
            "⚡ هل تريد دمج ملف JS (JavaScript)؟",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return JS_STATE

async def receive_css(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document or not document.file_name.endswith('.css'):
        await update.message.reply_text("⚠️ يرجى إرسال ملف CSS صحيح وامتداده `.css`!")
        return CSS_STATE
    
    tg_file = await document.get_file()
    file_bytes = await tg_file.download_as_bytearray()
    context.user_data['css'] = file_bytes.decode('utf-8')
    
    keyboard = [
        [InlineKeyboardButton("✅ نعم، أريد دمج JS", callback_data="yes_js")],
        [InlineKeyboardButton("❌ لا، ادمج الملفات الآن", callback_data="no_js")]
    ]
    await update.message.reply_text(
        "✅ تم استلام ملف CSS بنجاح.\n"
        "⚡ هل تريد دمج ملف JS (JavaScript)؟",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return JS_STATE

async def handle_js_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "yes_js":
        await query.message.edit_text("📎 أرسل ملف **JS** الآن:")
        return JS_STATE
    else:
        await query.message.edit_text("⏳ جاري دمج وتجهيز الملف النهائي...")
        return await process_and_send(update, context)

async def receive_js(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document or not document.file_name.endswith('.js'):
        await update.message.reply_text("⚠️ يرجى إرسال ملف JS صحيح وامتداده `.js`!")
        return JS_STATE
    
    tg_file = await document.get_file()
    file_bytes = await tg_file.download_as_bytearray()
    context.user_data['js'] = file_bytes.decode('utf-8')
    
    return await process_and_send(update, context)

async def process_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # تحديد مصدر الـ chat_id والمسؤول عن الإرسال سواء كان رسالة عادية أو ضغطة زرار
    if update.message:
        chat_id = update.effective_chat.id
        send_method = update.message.reply_document
    else:
        chat_id = update.effective_chat.id
        send_method = context.bot.send_document

    data = context.user_data
    html_content = data.get('html', '')
    css_content = data.get('css', '')
    js_content = data.get('js', '')
    
    # دمج الأكواد بذكاء داخل الـ HTML
    if css_content:
        if '</head>' in html_content:
            html_content = html_content.replace('</head>', f'<style>\n{css_content}\n</style>\n</head>')
        else:
            html_content = f"<style>\n{css_content}\n</style>\n" + html_content
            
    if js_content:
        if '</body>' in html_content:
            html_content = html_content.replace('</body>', f'<script>\n{js_content}\n</script>\n</body>')
        else:
            html_content = html_content + f"\n<script>\n{js_content}\n</script>"
    
    # إنشاء الملف في الذاكرة كـ BytesIO لإرساله مباشرة بدون حفظه على السيرفر لتوفير المساحة
    html_bytes = io.BytesIO(html_content.encode('utf-8'))
    html_bytes.name = "merged_project.html"
    
    await send_method(
        chat_id=chat_id,
        document=html_bytes,
        caption="🎉 تم دمج ملفاتك بنجاح في ملف HTML واحد جاهز للتشغيل!"
    )
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📥 تم إلغاء العملية الجارية. يمكنك البدء من جديد عبر /start")
    return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()
    
    # إعداد المحادثة المتكاملة وشروط التنقل
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            HTML_STATE: [MessageHandler(filters.Document.HTML, receive_html)],
            CSS_STATE: [
                CallbackQueryHandler(handle_css_choice, pattern="^(yes_css|no_css)$"),
                MessageHandler(filters.Document.CSS, receive_css)
            ],
            JS_STATE: [
                CallbackQueryHandler(handle_js_choice, pattern="^(yes_js|no_js)$"),
                MessageHandler(filters.Document.JAVASCRIPT, receive_js)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    app.add_handler(conv_handler)
    
    print("🤖 البوت يعمل بكفاءة ونظام الـ Conversation مضبوط...")
    app.run_polling()

if __name__ == '__main__':
    main()