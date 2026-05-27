import os
import logging
import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# حالات المحادثة
HTML_STATE, ASK_CSS, CSS_STATE, ASK_JS, JS_STATE = range(5)

TOKEN = os.getenv("TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = os.getenv("REPO_NAME", "gokermarke0-blip/222")

def get_github_pages_url():
    if REPO_NAME and "/" in REPO_NAME:
        user, repo = REPO_NAME.split("/")
        return f"https://{user}.github.io/{repo}/"
    return "https://gokermarke0-blip.github.io/222/"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "👋 مرحباً بك يا جوكر!\n\n"
        "🎯 أنا بوت لدمج ملفات الويب ونشرها فوراً.\n\n"
        "📁 أرسل لي ملف HTML الأساسي الآن:"
    )
    context.user_data.clear()
    return HTML_STATE

async def receive_html(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message.document:
        await update.message.reply_text("❌ من فضلك أرسل الملف كمستند (Document).")
        return HTML_STATE
    
    file = await update.message.document.get_file()
    html_content = (await file.download_as_bytearray()).decode('utf-8', errors='ignore')
    context.user_data['html'] = html_content
    
    reply_keyboard = [['✅ نعم', '❌ لا']]
    await update.message.reply_text(
        "✅ تم استلام ملف HTML.\n\n"
        "❓ هل تريد دمج ملف CSS؟",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return ASK_CSS

async def ask_css(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    answer = update.message.text
    if answer == '✅ نعم':
        await update.message.reply_text("🎨 أرسل ملف CSS الآن:")
        return CSS_STATE
    else:
        context.user_data['css'] = ""
        reply_keyboard = [['✅ نعم', '❌ لا']]
        await update.message.reply_text(
            "👍 تم تخطي CSS.\n\n❓ هل تريد دمج ملف JavaScript؟",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return ASK_JS

async def receive_css(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message.document:
        await update.message.reply_text("❌ أرسل ملف CSS كمستند.")
        return CSS_STATE
    
    file = await update.message.document.get_file()
    css_content = (await file.download_as_bytearray()).decode('utf-8', errors='ignore')
    context.user_data['css'] = css_content
    
    reply_keyboard = [['✅ نعم', '❌ لا']]
    await update.message.reply_text(
        "✅ تم استلام CSS.\n\n❓ هل تريد دمج ملف JavaScript؟",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return ASK_JS

async def ask_js(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    answer = update.message.text
    if answer == '✅ نعم':
        await update.message.reply_text("⚡ أرسل ملف JavaScript الآن:")
        return JS_STATE
    else:
        context.user_data['js'] = ""
        return await merge_and_deploy(update, context)

async def receive_js(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message.document:
        await update.message.reply_text("❌ أرسل ملف JS كمستند.")
        return JS_STATE
    
    file = await update.message.document.get_file()
    js_content = (await file.download_as_bytearray()).decode('utf-8', errors='ignore')
    context.user_data['js'] = js_content
    
    return await merge_and_deploy(update, context)

async def merge_and_deploy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("⏳ جاري دمج الملفات ونشر الموقع...")
    
    html = context.user_data.get('html', '')
    css = context.user_data.get('css', '')
    js = context.user_data.get('js', '')
    
    # دمج الأكواد
    merged = f"""<!DOCTYPE html>
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
    
    # رفع على جيت هب
    if GITHUB_TOKEN and REPO_NAME:
        user, repo = REPO_NAME.split("/")
        api_url = f"https://api.github.com/repos/{user}/{repo}/contents/index.html"
        import base64
        content_b64 = base64.b64encode(merged.encode('utf-8')).decode('utf-8')
        
        # جلب الـ SHA للملف القديم
        response = requests.get(api_url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
        sha = response.json().get('sha') if response.status_code == 200 else None
        
        # رفع الملف الجديد
        data = {"message": "Update via Telegram Bot", "content": content_b64}
        if sha:
            data["sha"] = sha
        
        requests.put(api_url, json=data, headers={"Authorization": f"token {GITHUB_TOKEN}"})
        logger.info("✅ تم الرفع على جيت هب!")
    
    site_url = get_github_pages_url()
    
    await update.message.reply_text(
        f"🎉 **تم بنجاح!**\n\n"
        f"🔗 رابط موقعك:\n{site_url}\n\n"
        f"📋 ابعته لأي شخص يشوف الموقع!",
        parse_mode="Markdown"
    )
    
    context.user_data.clear()
    return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()
    
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            HTML_STATE: [MessageHandler(filters.Document.ALL, receive_html)],
            ASK_CSS: [MessageHandler(filters.TEXT, ask_css)],
            CSS_STATE: [MessageHandler(filters.Document.ALL, receive_css)],
            ASK_JS: [MessageHandler(filters.TEXT, ask_js)],
            JS_STATE: [MessageHandler(filters.Document.ALL, receive_js)],
        },
        fallbacks=[],
    )
    
    app.add_handler(conv)
    app.run_polling()

if __name__ == '__main__':
    main()
