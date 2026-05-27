import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 **بوت تحميل الفيديو!**\n\n"
        "📎 أرسل رابط فيديو من:\n"
        "• YouTube\n"
        "• TikTok\n"
        "• Twitter\n"
        "• Facebook",
        parse_mode="Markdown"
    )

async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http"):
        await update.message.reply_text("⚠️ ارسل رابط صحيح!")
        return
    
    await update.message.reply_text("⏳ جاري التحميل...")
    
    try:
        import subprocess
        result = subprocess.run(
            ['yt-dlp', '-f', 'best', '-o', 'video.mp4', url],
            capture_output=True, text=True
        )
        
        # إرسال الملف
        try:
            with open('video.mp4', 'rb') as f:
                await update.message.reply_video(video=f, caption="✅ تم التحميل!")
            import os
            os.remove('video.mp4')
        except:
            await update.message.reply_text(f"❌ خطأ: {result.stderr}")
            
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {str(e)}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download))
    app.run_polling()

if __name__ == '__main__':
    main()
