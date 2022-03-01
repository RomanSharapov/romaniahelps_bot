#!/usr/bin/env python
# pylint: disable=C0116,W0613
# This program is dedicated to the public domain under the CC0 license.

import logging
import smtplib

from email.message import EmailMessage
from typing import Dict

from telegram import (
    KeyboardButton,
    ParseMode,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
)

import config

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)

HELP_NEEDED, LOCATION, CONTACTS, CONTACTS_VERIFICATION = range(4)


def escape_markdown(text: str) -> str:
    special_characters = "\{}[]()#+-.!"
    for ch in special_characters:
        if ch in text:
            text = text.replace(ch, f"\{ch}")
    return text


def send_email(user_data: Dict[str, Dict[str, str]]) -> None:
    """Sends email with the user data to the specified SMTP server."""
    email_user = config.EMAIL_USER
    email_password = config.EMAIL_PASSWD

    msg = EmailMessage()

    def data_pprint(user_data: Dict[str, Dict[str, str]]) -> str:
        result = []
        for key, value in user_data.items():
            result.append(f"User with id {key} requested the following help:")
            result.append(f"My name is {value['user_firstname']},")
            if value["user_username"]:
                result.append(f"and username is @{value['user_username']}.")
            else:
                result.append(f"and I haven't configured a username, sorry.")
            result.append(f"I need help with: {value['help_needed']}")
            result.append(f"My coordinates: {value['location']}")
            result.append(f"My contacts: {value['contacts']}")
            result.append(f"Additional contacts: {value['additional_contacts']}")
        return "\n".join(result)

    msg.set_content(
        f"Hey Volunteers,\n\n{data_pprint(user_data)}"
    )

    msg["Subject"] = "[Bot] Help needed!"
    msg["From"] = email_user
    msg["To"] = config.SEND_MESSAGES_TO

    try:
        server = smtplib.SMTP_SSL(config.EMAIL_SERVER, config.EMAIL_PORT)
        server.ehlo()
        server.login(email_user, email_password)
        server.send_message(msg)
        server.quit()

        logger.info("Email sent successfully!")
    except Exception as e:
        logger.error("Something went wrong with email...")
        logger.error(e)


def start(update: Update, context: CallbackContext) -> int:
    """Starts the conversation and asks the user about help message."""

    update.message.reply_text(
        escape_markdown(
            "🇺🇦 Привiт! Romanians Help Бот допоможе вам зв'язатися з волонтерами в Румунії. "
            "Надішліть або натисніть /cancel, щоб припинити взаємодію.\n\n"
            "*Яка допомога вам потрібна (наприклад, житло, їжа чи щось інше)?*\n\n"
            "🇷🇺 Привет! Romanians Help Бот поможет вам связаться с волонтерами из Румынии. "
            "Напиши или нажми /cancel для прекращения общения с ботом.\n\n"
            "*Какая помощь требуется (например, жильё, питание или ещё что-то)?*\n\n"
            "🇺🇲 Hi! Romanians Help Bot will help you to connect with volunteers in Romania. "
            "Send or hit /cancel to stop interaction.\n\n"
            "*What kind of help do you need (e.g. accomodation, food, or something else)?*"
        ),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=ReplyKeyboardRemove(),
    )

    return HELP_NEEDED


def help_needed(update: Update, context: CallbackContext) -> int:
    """Stores the help message and asks for the user's location."""
    user = update.message.from_user
    text = update.message.text

    context.user_data[user.id] = {}
    context.user_data[user.id]["user_firstname"] = user.first_name
    context.user_data[user.id]["user_username"] = user.username
    context.user_data[user.id]["help_needed"] = text

    logger.info("User with username %s needs help with: %s", user.username, text)

    update.message.reply_text(
        "🇺🇦 Розумію! Будь ласка, поділіться своїм поточним місцезнаходженням, "
        "щоб волонтери могли знайти вас, або надішлить /skip, "
        "якщо ви не хочете ділитися своїм поточним місцезнаходженням.\n\n"
        "🇷🇺 Понятно! Пожалуйста, поделитесь своим местоположением или укажите точку встречи для того, "
        "чтобы волонтёры могли вас найти. Напишите /skip, если не хотите делиться местоположением.\n\n"
        "🇺🇲 I see! Please share your current location or venue, "
        "so volunteers can find you, or send /skip if you don't want to.",
    )

    return LOCATION


def location(update: Update, context: CallbackContext) -> int:
    """Stores the location and asks for some the user's contacts."""
    user = update.message.from_user
    user_location = update.message.location

    user_data = context.user_data
    user_data[user.id]["location"] = ", ".join((str(user_location.latitude), str(user_location.longitude)))

    logger.info(
        "Location of %s: %f / %f", user.first_name, user_location.latitude, user_location.longitude
    )

    contact_button = [[KeyboardButton(text="Send my contacts", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(contact_button, one_time_keyboard=True, resize_keyboard=True)
    update.message.reply_text(
        escape_markdown(
            "🇺🇦 Дякую! Наостанок скажіть мені, як наші волонтери можуть з вами зв’язатися.\n"
            "*⚠ Увага!\nБудь ласка, надішліть свій номер телефону, натиснувши кнопку знизу "
            "або вкажіть свою адресу електронної пошти.*\n\n"
            "🇷🇺 Спасибо! Наконец, скажите мне, как наши волонтёры могут с вами связаться.\n"
            "*⚠ Внимание!\nПожалуйста, отправьте свой номер телефона нажав кнопку внизу "
            "или укажите свой адрес электронной почты.*\n\n"
            "🇺🇲 Thank you! At last, tell me how our volunteers can contact you.\n"
            "*⚠ Important!\nPlease provide your phone number by clicking the button below or type your email address.*"
        ),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=reply_markup,
    )

    return CONTACTS


def skip_location(update: Update, context: CallbackContext) -> int:
    """Skips the location and asks for the user contacts."""
    user = update.message.from_user
    user_data = context.user_data
    user_data[user.id]["location"] = ("unknown", "unknown")

    logger.info("User %s did not send a location.", user.first_name)

    contact_button = [[KeyboardButton(text="Send my phone number", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(contact_button, one_time_keyboard=True, resize_keyboard=True)
    update.message.reply_text(
        escape_markdown(
            "🇺🇦 Не проблема, ми поважаємо вашу конфіденційність! "
            "Наостанок скажіть мені, як наші волонтери можуть з вами зв’язатися.\n"
            "*⚠ Увага!\nБудь ласка, надішліть свій номер телефону, натиснувши кнопку знизу "
            "або вкажіть свою адресу електронної пошти.*\n\n"
            "🇷🇺 Не проблема, мы уважаем вашу конфиденциальность! "
            "Наконец, скажите мне, как наши волонтёры могут с вами связаться.\n"
            "*⚠ Внимание!\nПожалуйста, отправьте свой номер телефона нажав кнопку внизу "
            "или укажите свой адрес электронной почты.*\n\n"
            "🇺🇲 That's fine, we respect your privacy! At last, tell me how our volunteers can contact you.\n"
            "*⚠ Important!\nPlease provide your phone number by clicking the button below or type your email address.*"
        ),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=reply_markup,
    )

    return CONTACTS


def contacts(update: Update, context: CallbackContext) -> int:
    """Stores the info about the user and ends the conversation."""
    user = update.message.from_user
    user_data = context.user_data
    text = update.message.text
    contacts = update.message.contact

    if text is None:
        contact_string = f"{contacts.first_name} {contacts.last_name}, phone number: +{contacts.phone_number}"
        context.user_data[user.id]["contacts"] = contact_string
        logger.info("Phone number of %s %s: %s", contacts.first_name, contacts.last_name, contacts.phone_number)
    else:
        context.user_data[user.id]["contacts"] = f"{user.first_name} {user.last_name}, contact info: {text}"
        logger.info("Contacts of %s %s: %s", user.first_name, user.last_name, text)

    contact_button = [[KeyboardButton(text="Confirm")]]
    reply_markup = ReplyKeyboardMarkup(contact_button, one_time_keyboard=True, resize_keyboard=True)
    update.message.reply_text(
        escape_markdown(
            "🇺🇦 Будь ласка, перевірте свої контактні дані, щоб переконатися, "
            "що волонтери зможуть з вами зв'язатися.\n"
            "Якщо все добре, натисніть кнопку Confirm. Якщо потрібно надати додаткову інформацію, "
            "напишіть її у повідомленні.\n\n"
            "🇷🇺 Пожалуйста, проверьте свои контактные данные для того, чтобы убедиться, "
            "что волонтёры смогут с вами связаться.\n"
            "Если всё хорошо, нажмите кнопку Confirm. Если нужно предоставить дополнительную информацию, "
            "напишите её в сообщении.\n\n"
            "🇺🇲 Please, verify your contacts to make sure our volunteers will be able to contact you.\n"
            "If everything is ok, tap Confirm button below. If you need to provide more info, feel free to "
            "write your contacts.\n\n"
            f"📞➡ *{context.user_data[user.id]['contacts']}*"
        ),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=reply_markup,
    )

    return CONTACTS_VERIFICATION


def contacts_verification(update: Update, context: CallbackContext) -> int:
    """Verifies the info about the user and ends the conversation."""
    user = update.message.from_user
    user_data = context.user_data

    context.user_data[user.id]["additional_contacts"] = update.message.text

    update.message.reply_text(
        escape_markdown(
            "🇺🇦 Дякую! Румунські волонтери незабаром зв’яжуться з вами.\n"
            "Якщо ми не відповімо протягом декількох годин, будь ласка, напишіть нам на email "
            f"{config.EMAIL_USER}. Номер вашої заявки `{user.id}`, використовуйте його для звернення.\n\n"
            "🇷🇺 Спасибо! Румынские волонтёры скоро свяжутся с вами.\n"
            f"Если мы не ответим в течении нескольких часов, пожалуйста, напишите нам на email "
            f"{config.EMAIL_USER}. Номер вашей заявки `{user.id}`, используйте его для обращения.\n\n"
            "🇺🇲 Thank you! Romanian volunteers will reach out shortly.\n"
            "If we won't be able to reply within several hours, please, write to our email "
            f"{config.EMAIL_USER}. Your request number is `{user.id}`, use it to submit your request."
        ),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=ReplyKeyboardRemove(),
    )

    send_email(user_data)
    logger.info("Gathered data: %s", user_data)

    return ConversationHandler.END


def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    user_data = context.user_data

    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text(
        escape_markdown(
            "🇺🇦 Взаємодія скасована! Залишайтесь у безпеці.\n\n"
            "🇷🇺 Взаимодействие с ботом прекращено! Берегите себя.\n\n"
            "🇺🇲 Interaction canceled! Stay safe."
        ),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=ReplyKeyboardRemove(),
    )

    user_data.clear()
    return ConversationHandler.END


def main() -> None:
    """Run the bot."""

    updater = Updater(config.BOT_TOKEN)

    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler(["start", "starthelp"], start)],
        states={
            HELP_NEEDED: [MessageHandler(Filters.text & ~Filters.command, help_needed)],
            LOCATION: [
                MessageHandler(Filters.location, location),
                CommandHandler("skip", skip_location),
            ],
            CONTACTS: [MessageHandler((Filters.text | Filters.contact) & ~Filters.command, contacts)],
            CONTACTS_VERIFICATION: [MessageHandler(Filters.text & ~Filters.command, contacts_verification)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    dispatcher.add_handler(conv_handler)

    updater.start_webhook(
        listen="0.0.0.0",
        port=config.PORT,
        url_path=config.BOT_TOKEN,
        webhook_url=f"{config.BOT_URL}{config.BOT_TOKEN}",
    )

    updater.idle()


if __name__ == "__main__":
    main()
