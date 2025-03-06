import logging
import requests
from typing import Final
from bs4 import BeautifulSoup
import datetime
import time
import pytz
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Use an environment variable for security
BOT_TOKEN: Final = "7511673565:AAGZnohzoxAgJDulJKWMiaqxjs1AZ-_Fn2c"

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ✅ URLs for USD & EUR Prices
DOLLAR_URL = "https://alanchand.com/currencies-price/usd"
EURO_URL = "https://alanchand.com/currencies-price/eur"

# ✅ Function to Fetch Prices with Retry Mechanism
def get_price(url):
    while True:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Find the first <td> tag containing the price
            usd_price_tags = soup.find_all("td", {"data-v-c1354816": True}, limit=2)
            return usd_price_tags[1].text.replace(" تومان", "").strip()

        except (requests.RequestException, AttributeError):
            pass  # Ignore errors and retry

        time.sleep(2)  # Retry after 2 seconds

# ✅ Function to Get Both USD & EUR Prices
async def fetch_prices():
    loop = asyncio.get_running_loop()
    usd_price = await loop.run_in_executor(None, get_price, DOLLAR_URL)
    eur_price = await loop.run_in_executor(None, get_price, EURO_URL)
    return usd_price, eur_price

# ✅ Start Command
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Hi {update.effective_user.first_name}! I'm a bot! Thanks for using me!"
    )

# ✅ Function to Check if a Job Already Exists
def check_price_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE):
    return bool(context.job_queue.get_jobs_by_name(name))

# ✅ Command to Start Price Updates
async def price_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    job_name = str(update.effective_user.id)

    # If the user already has a job, prevent duplicates
    if check_price_job_if_exists(job_name, context):
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="You already have a job running, please unset it first.")
        return

    data = await fetch_prices()
    price_message = f"From now on, you will receive price updates every 1.5 hours:\nUSD: {data[0]}\nEUR: {data[1]}"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=price_message)

    # Define Tehran timezone
    tehran_tz = pytz.timezone("Asia/Tehran")

    # Define exact send times
    send_times = [
        datetime.time(8, 0, tzinfo=tehran_tz),
        datetime.time(9, 30, tzinfo=tehran_tz),
        datetime.time(11, 0, tzinfo=tehran_tz),
        datetime.time(12, 30, tzinfo=tehran_tz),
        datetime.time(14, 0, tzinfo=tehran_tz),
        datetime.time(15, 30, tzinfo=tehran_tz),
        datetime.time(17, 0, tzinfo=tehran_tz),
        datetime.time(18, 30, tzinfo=tehran_tz),
        datetime.time(20, 0, tzinfo=tehran_tz),
        datetime.time(21, 30, tzinfo=tehran_tz),
        datetime.time(23, 0, tzinfo=tehran_tz),
    ]

    # Schedule jobs
    for t in send_times:
        context.job_queue.run_daily(
            lambda context: asyncio.create_task(job_price_handler(context)),  # Fix async issue
            time=t,
            chat_id=update.effective_chat.id,
            name=job_name
        )

# ✅ Command to Unset the Job
async def unset_price_job_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jobs = context.job_queue.get_jobs_by_name(str(update.effective_user.id))
    for job in jobs:
        job.schedule_removal()
    await context.bot.send_message(chat_id=update.effective_chat.id, text="You will no longer receive price updates.")

# ✅ Function to Send the USD Price
async def job_price_handler(context: ContextTypes.DEFAULT_TYPE):
    data = await fetch_prices()
    price_message = f"USD: {data[0]}\nEUR: {data[1]}"
    await context.bot.send_message(chat_id=context.job.chat_id, text=price_message)

# ✅ Main Function
if __name__ == "__main__":
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("price", price_handler))
    application.add_handler(CommandHandler("unset", unset_price_job_handler))

    application.run_polling()
