import os
import io
import logging
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
from card_generator import generate_business_card

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

(NAME, TITLE, COMPANY, PHONE, EMAIL, WEBSITE, SOCIAL, PHOTO) = range(8)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "👋 *Welcome to Business Card Maker!*\n\n"
        "I'll walk you through creating a sleek, professional business card image.\n\n"
        "You can type /cancel at any time to stop.\n\n"
        "Let's start — what's your *full name*?",
        parse_mode="Markdown",
    )
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text("Great! What's your *job title*?", parse_mode="Markdown")
    return TITLE


async def get_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["title"] = update.message.text.strip()
    await update.message.reply_text("🏢 What's your *company name*?", parse_mode="Markdown")
    return COMPANY


async def get_company(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["company"] = update.message.text.strip()
    await update.message.reply_text("📞 What's your *phone number*?", parse_mode="Markdown")
    return PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["phone"] = update.message.text.strip()
    await update.message.reply_text("📧 What's your *email address*?", parse_mode="Markdown")
    return EMAIL


async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["email"] = update.message.text.strip()
    await update.message.reply_text(
        "🌐 What's your *website URL*?\n(e.g. www.example.com)",
        parse_mode="Markdown",
    )
    return WEBSITE


async def get_website(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["website"] = update.message.text.strip()
    await update.message.reply_text(
        "📱 Add your *social media handles*.\n\n"
        "One per line, like:\n"
        "LinkedIn: linkedin.com/in/yourname\n"
        "Twitter: @yourhandle\n"
        "Instagram: @yourhandle\n\n"
        "Or send /skip to leave this blank.",
        parse_mode="Markdown",
    )
    return SOCIAL


async def get_social(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["social"] = update.message.text.strip()
    await update.message.reply_text(
        "🖼️ Finally, send your *profile photo*.\n\n"
        "Or /skip to use an initials avatar.",
        parse_mode="Markdown",
    )
    return PHOTO


async def skip_social(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["social"] = None
    await update.message.reply_text(
        "🖼️ Send your *profile photo*, or /skip to use an initials avatar.",
        parse_mode="Markdown",
    )
    return PHOTO


async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    context.user_data["photo"] = bytes(photo_bytes)
    return await _build_and_send(update, context)


async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["photo"] = None
    return await _build_and_send(update, context)


async def _build_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("✨ Generating your business card...")
    try:
        card = generate_business_card(context.user_data)
        buf = io.BytesIO()
        card.save(buf, format="PNG", dpi=(300, 300))
        buf.seek(0)
        await update.message.reply_photo(
            photo=buf,
            caption=f"🎉 Here's your business card, {context.user_data['name']}!\n\nUse /start to create another one.",
        )
    except Exception as e:
        logger.error("Card generation failed: %s", e)
        await update.message.reply_text(
            "❌ Something went wrong. Please try /start again."
        )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "❌ Cancelled. Use /start whenever you're ready.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


def main() -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    webhook_url = os.environ.get("WEBHOOK_URL", "").rstrip("/")
    port = int(os.environ.get("PORT", 0))

    app = Application.builder().token(token).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME:    [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            TITLE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, get_title)],
            COMPANY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_company)],
            PHONE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            EMAIL:   [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)],
            WEBSITE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_website)],
            SOCIAL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_social),
                CommandHandler("skip", skip_social),
            ],
            PHOTO: [
                MessageHandler(filters.PHOTO, get_photo),
                CommandHandler("skip", skip_photo),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv)

    if webhook_url and port:
        logger.info("Starting webhook on port %d", port)
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=token,
            webhook_url=f"{webhook_url}/{token}",
        )
    else:
        logger.info("Starting polling")
        app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
