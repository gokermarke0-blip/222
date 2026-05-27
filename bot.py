import os
import requests
from telegram import Update, ForceReply
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("TOKEN")

# مكتبات التحميل
try:
    from yt_dlp import YTDLPTools as ytdlp
except:
    ytdlp = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 **مرحباً بك في بوت تحميل الفيديو!**\n\n"
        "📎 أرسل لي رابط أي فيديو من:\n"
        "• YouTube\n"
        "• TikTok\n"
        "• Instagram\n"
        "• Twitter\n"
        "• Facebook\n"
        "• أو أي منصة أخرى",
        parse_mode="Markdown"
    )

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    # التحقق إنه رابط
    if not url.startswith("http"):
        await update.message.reply_text("⚠️ من فضلك أرسل رابط صحيح!")
        return
    
    await update.message.reply_text("⏳ جاري التحميل...")
    
    try:
        # خيارات التحميل
        ydl_opts = {
            'format': 'best',
            'outtmpl': 'download.%(ext)s',
            'quiet': True,
            'no_warnings': True,
        }
        
        with ytdlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        
        # إرسال الفيديو
        with open(filename, 'rb') as f:
            await update.message.reply_video(
                video=f,
                caption=f"✅ تم تحميل: {info.get('title', 'فيديو')}"
            )
        
        # حذف الملف لتوفير المساحة
        os.remove(filename)
        
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ في التحميل: {str(e)}")

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))
    
    print("🤖 بوت تحميل الفيديو يعمل...")
    app.run_polling()

if __name__ == '__main__':
    main()
