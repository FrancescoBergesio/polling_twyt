#!/usr/bin/python3

import logging

from telegram.ext import Updater, CommandHandler

import requests as r

from datetime import datetime
from datetime import timedelta

import time

import math

# Google
google_api = '[Google API key]'
youtube_channel =  '[Youtube channel ID]'

# Telegram
chat_id = -0 #[Telegram chat ID]
bot_key = '[Telegram Bot API key]'

# Twitch
twitch_api_client_id = '[Twitch API ClientID]'
twitch_api_secret = '[Twitch API Secret]'
twitch_api_token = ''
twitch_channel = '[Twitch channel login name]'

# Formats
youtube_format = 'https://www.youtube.com/watch?v={}'
twitch_format = 'Title: {}\nType: {}\nhttps://www.twitch.tv/{}'
status_format = 'Chat: {}\nLast twitch: {}\nLast youtube: {}\n'

# Previous
prev_tw = 'None'
prev_yt = 'None'

# Sleeps
sleep = 300
yt_sleep = 3

# Permissions
superusers = {0} #[UserID that can start the bot]

# Requests
req_yt = 'https://www.googleapis.com/youtube/v3/search?key={}&channelId={}&part=snippet,id&order=date&maxResults=1'
req_tw = 'https://api.twitch.tv/helix/streams?user_login={}'
req_tw_token = 'https://id.twitch.tv/oauth2/token?client_id={}&client_secret={}&grant_type=client_credentials'

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

# Start bot requests
def start(update, context):
    global chat_id, sleep, yt_sleep
    user = update.message.from_user.id
    update.message.reply_text(':)')
    if user in superusers:
        update.message.reply_text('Synchronization ...')
        minutes = datetime.now().minute
        seconds = datetime.now().second
        wait = 5 - ((minutes - 1) % 5)
        time.sleep(wait * 60 - seconds)
        minutes = datetime.now().minute - 1
        yt_sleep = (3 - (minutes % 15) / 5) 
        yt_sleep = math.trunc(yt_sleep) % 3 + 1
        job_removed = remove_job_if_exists(str(chat_id), context)
        context.job_queue.run_once(notify, 0, context=chat_id, name=str(chat_id))
        update.message.reply_text('Complete')
 
# Get bot status
def status(update, context):
    global chat_id, prev_yt, prev_tw, status_format
    user = update.message.from_user.id
    update.message.reply_text(status_format.format(chat_id, prev_tw, prev_yt))

# Stop bot requests
def stop(update, context):
    global chat_id
    remove_job_if_exists(str(chat_id), context)
    update.message.reply_text(':\'(')

# Check youtube
def notify_yt(context, job):
    global google_api, youtube_channel, sleep, prev_yt, youtube_format
    res = r.get(req_yt.format(google_api, youtube_channel)).json()
    publish = datetime.strptime(res['items'][0]['snippet']['publishedAt'],"%Y-%m-%dT%H:%M:%SZ")
    if  datetime.now() - publish <= timedelta(hours = 2, seconds = sleep*3):
        context.bot.send_message(job.context, text=youtube_format.format(res['items'][0]['id']['videoId']))
    prev_yt = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")

# Check twitch
def notify_tw(context, job):
    global sleep, twitch_api_token, twitch_api_secret, twitch_api_client_id, req_tw, req_tw_token, prev_tw, twitch_channel, twitch_format
    res = r.get(req_tw, headers={'Authorization': 'Bearer {}'.format(twitch_api_token), 'Client-Id': twitch_api_client_id})
    if not res.ok:
        res = r.post(req_tw_token.format(twitch_api_client_id, twitch_api_secret)).json()
        twitch_api_token = res['access_token']
        res = r.get(req_tw, headers={'Authorization': 'Bearer {}'.format(twitch_api_token), 'Client-Id': twitch_api_client_id})
    res = res.json()
    if len(res['data']) != 0:
        started = datetime.strptime(res['data'][0]['started_at'],"%Y-%m-%dT%H:%M:%SZ")
        if datetime.now() - started <= timedelta(hours = 2, seconds = sleep): # CET
            context.bot.send_message(job.context, text=twitch_format.format(res['data'][0]['title'], res['data'][0]['description'] if 'description' in res['data'][0] else '', twitch_channel))
    prev_tw = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")

# Check new content
def notify(context):
    global yt_sleep
    job = context.job
    remove_job_if_exists(str(chat_id), context)
    context.job_queue.run_once(notify, sleep, context=chat_id, name=str(chat_id))
    yt_sleep -= 1 
    if yt_sleep == 0:
        notify_yt(context, job)
        yt_sleep = 3
    notify_tw(context, job)

# Remove previous job
def remove_job_if_exists(name, context):
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True

def main():
    global bot_key
    updater = Updater(bot_key)

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("stop", stop))
    dispatcher.add_handler(CommandHandler("status", status))

    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()
