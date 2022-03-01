import os

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
