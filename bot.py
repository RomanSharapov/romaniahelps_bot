#!/usr/bin/env python
# pylint: disable=C0116,W0613
# This program is dedicated to the public domain under the CC0 license.

import logging
import os
import smtplib

from email.message import EmailMessage
from typing import Dict

from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
)

PORT = int(os.environ.get("PORT", 8443))

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if BOT_TOKEN is None:
    raise EnvironmentError("Please, set BOT_TOKEN environment variable with the bot token from @BotFather")
BOT_URL = "https://romanianshelp.herokuapp.com/"

EMAIL_SERVER = "smtp.gmail.com"
EMAIL_PORT = 465
EMAIL_USER = "romanianshelp@gmail.com"
EMAIL_PASSWD = os.environ.get("EMAIL_PASSWD")
if EMAIL_PASSWD is None:
    raise EnvironmentError("Please, set EMAIL_PASSWD environment variable with the emal password")

SEND_MESSAGES_TO = "support@romanianshelp.zendesk.com"

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

HELP_NEEDED, LOCATION, CONTACTS = range(3)


def send_email(user_data: Dict[str, Dict[str, str]]) -> None:
    """Sends email with the user data to the specified SMTP server."""
    email_user = EMAIL_USER
    email_password = EMAIL_PASSWD

    msg = EmailMessage()

    def data_pprint(user_data: Dict[str, Dict[str, str]]) -> str:
        result = []
        for key, value in user_data.items():
            result.append(f"User with id {key} requested the following help:")
            result.append(f"My name is {value['user_name']},")
            result.append(f"I need help with: {value['help_needed']}")
            result.append(f"My coordinates: {value['location']}")
            result.append(f"My contacts: {value['contacts']}")
        return '\n'.join(result)

    msg.set_content(
        f"Hey Volunteers,\n\n{data_pprint(user_data)}"
    )

    msg['Subject'] = '[Bot] Help needed!'
    msg['From'] = email_user
    msg['To'] = SEND_MESSAGES_TO

    try:
        server = smtplib.SMTP_SSL(EMAIL_SERVER, EMAIL_PORT)
        server.ehlo()
        server.login(email_user, email_password)
        server.send_message(msg)
        server.quit()

        logger.info('Email sent successfully!')
    except Exception as e:
        logger.error('Something went wrong with email...')
        logger.error(e)


def start(update: Update, context: CallbackContext) -> int:
    """Starts the conversation and asks the user about help message."""

    update.message.reply_text(
        'Hi! Romanians Help Bot will help you to connect with volunteers in Romania. '
        'Send or hit /cancel to stop interaction.\n\n'
        'What kind of help do you need (e.g. accomodation, food, or something else)?',
    )

    return HELP_NEEDED


def help_needed(update: Update, context: CallbackContext) -> int:
    """Stores the help message and asks for the user's location."""
    user = update.message.from_user
    text = update.message.text

    context.user_data[user.id] = {}
    context.user_data[user.id]['user_name'] = user.first_name
    context.user_data[user.id]['help_needed'] = text

    logger.info("User %s needs help with: %s", user.first_name, text)

    update.message.reply_text(
        'I see! Please share your current location or venue, '
        'so volunteers can find you, or send /skip if you don\'t want to.',
    )

    return LOCATION


def location(update: Update, context: CallbackContext) -> int:
    """Stores the location and asks for some the user's contacts."""
    user = update.message.from_user
    user_location = update.message.location

    user_data = context.user_data
    user_data[user.id]['location'] = ", ".join((str(user_location.latitude), str(user_location.longitude)))

    logger.info(
        "Location of %s: %f / %f", user.first_name, user_location.latitude, user_location.longitude
    )

    contact_button = [[KeyboardButton(text="Send my contacts", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(contact_button, one_time_keyboard=True)
    update.message.reply_text(
        'Thank you! At last, tell me how our volunteers can contact you.',
        reply_markup=reply_markup,
    )

    return CONTACTS


def skip_location(update: Update, context: CallbackContext) -> int:
    """Skips the location and asks for the user contacts."""
    user = update.message.from_user
    user_data = context.user_data
    user_data[user.id]['location'] = ("unknown", "unknown")

    logger.info("User %s did not send a location.", user.first_name)

    contact_button = [[KeyboardButton(text="Send my contacts", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(contact_button, one_time_keyboard=True)
    update.message.reply_text(
        'That\'s fine, we respect your privacy! At last, tell me how our volunteers can contact you.',
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
        context.user_data[user.id]['contacts'] = contact_string
        logger.info("Phone number of %s %s: %s", contacts.first_name, contacts.last_name, contacts.phone_number)
    else:
        context.user_data[user.id]['contacts'] = update.message.text
        logger.info("Contacts of %s: %s", user.first_name, text)

    update.message.reply_text(
        'Thank you! Romanian volunteers will reach out to you shortly.',
        reply_markup=ReplyKeyboardRemove()
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
        'Interaction canceled! Stay safe.',
        reply_markup=ReplyKeyboardRemove(),
    )

    user_data.clear()
    return ConversationHandler.END


def main() -> None:
    """Run the bot."""

    updater = Updater(BOT_TOKEN)

    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler(['start', 'starthelp'], start)],
        states={
            HELP_NEEDED: [MessageHandler(Filters.text & ~Filters.command, help_needed)],
            LOCATION: [
                MessageHandler(Filters.location, location),
                CommandHandler('skip', skip_location),
            ],
            CONTACTS: [MessageHandler((Filters.text | Filters.contact) & ~Filters.command, contacts)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(conv_handler)

    updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"{BOT_URL}{BOT_TOKEN}",
    )

    updater.idle()


if __name__ == '__main__':
    main()
