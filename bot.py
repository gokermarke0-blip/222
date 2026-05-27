import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# إعداد الـ Logs عشان لو فيه أي مشكلة نشوفها
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 **مرحباً بك يا جوكر في بوت تحميل الفيديوهات السريع!**\n\n"
        "🎬 ابعتلي لينك أي فيديو من (تيك توك، إنستغرام، يوتيوب، تويتر، فيسبوك، كواي) "
        "وهنزله لك فوراً وبأعلى جودة متاحة! 🔥",
        parse_mode="Markdown"
    )

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    
    # التأكد إن المرسل هو لينك فعلاً
    if not url.startswith(("http://", "https://")):
        return # لو مش لينك مش هيرد عشان ميزعجش المستخدم

    waiting_message = await update.message.reply_text("⏳ **جاري فحص اللينك وتحميل الفيديو... انتظر ثانية**")

    # إعدادات مكتبة yt-dlp للتحميل بأفضل جودة مدمجة (فيديو وصوت معاً) وحجم مناسب للتليجرام
    ydl_opts = {
        'format': 'best[ext=mp4]/best', # بيجيب فيديو بصيغة mp4 جاهز للعرض في التليجرام
        'outtmpl': 'downloads/%(id)s.%(ext)s', # حفظ الملف في فولدر مؤقت باسم الأيدي بتاعه
        'max_filesize': 50 * 1024 * 1024, # حد أقصى 50 ميجا عشان قيود التليجرام للبوتات العادية
        'quiet': True,
        'no_warnings': True,
    }

    # تشغيل التحميل في خلفية منفصلة عشان البوت ميهنجش لو كذا حد استخدمه
    def run_ydl():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            # التأكد من امتداد الملف المناسب
            if not os.path.exists(filename) and os.path.exists(filename.replace('.mp4', '.mkv')):
                filename = filename.replace('.mp4', '.mkv')
            return filename, info.get('title', 'Video')

    try:
        # تنفيذ دالة التحميل بدون تعطيل البوت
        loop = asyncio.get_running_loop()
        file_path, video_title = await loop.run_in_executor(None, run_ydl)

        if os.path.exists(file_path):
            await waiting_message.edit_text("🚀 **جاري رفع الفيديو للتليجرام...**")
            
            # إرسال الفيديو كـ Video مش ملف عشان يشتغل جوه الشات علطول
            with open(file_path, 'rb') as video_file:
                await update.message.reply_video(
                    video=video_file,
                    caption=f"🎬 **{video_title}**\n\n✨ تم التحميل بنجاح بواسطة بوت جوكر!",
                    supports_streaming=True # تتيح للمستخدم تشغيل الفيديو أثناء التحميل
                )
            
            # مسح الملف فوراً من السيرفر بعد الرفع عشان ميمشيش مساحة السيرفر
            os.remove(file_path)
            await waiting_message.delete()
        else:
            await waiting_message.edit_text("❌ عذراً، تعذر العثور على ملف الفيديو بعد تحميله.")

    except yt_dlp.utils.MaxFileSizeReachedError:
        await waiting_message.edit_text("⚠️ حجم الفيديو كبير جداً (أكبر من 50 ميجابايت). لا يمكن إرساله عبر البوت.")
    except Exception as e:
        logger.error(f"Download error: {e}")
        await waiting_message.edit_text("❌ حصلت مشكلة أثناء التحميل! اتأكد إن اللينك شغال ومفتوح للعامة.")

def main():
    if not TOKEN:
        logger.error("❌ TOKEN مش موجود في الـ Environment Variables!")
        return
        
    # إنشاء فولدر التحميلات المؤقتة لو مش موجود
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    # البوت هيقرأ أي نص مبعوت ويشوف لو لينك هيحمله فوراً
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))

    application.run_polling()

if __name__ == '__main__':
    main()
