# !/usr/bin/env python3
import difflib
import os
import re
import time
import asyncio
import asyncio.subprocess
import logging
from telethon import TelegramClient, events, errors
from telethon.tl.types import MessageMediaWebPage

#***********************************************************************************#
api_id = os.environ.get('API_ID')   # your telegram api id
api_hash = os.environ.get('API_HASH')  # your telegram api hash
bot_token = os.environ.get('BOT_TOKEN')  # your bot_token
admin_id = os.environ.get('ADMIN_ID')  # your user id
save_path = 'downloads'  # Dont change this unless you know what you are doing
upload_file_set = False  # set upload file to google drive
drive_id = os.environ.get('DRIVE_ID')  # Folder ID of Teamdrive
drive_name = 'GC'  # Dont change this unless you know what you are doing
max_num = 10  # Simultaneous downloads
# filter file name/File name filtering
filter_list = ['Hello, welcome to join Quantumu',
               '\n']
# filter chat id /Filter some channels not to download
blacklist = [1388464914,]
donwload_all_chat = False # Monitor all the channels you have joined. New messages received will be downloaded if they contain media, which is closed by default
#***********************************************************************************#

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.WARNING)
logger = logging.getLogger(__name__)
queue = asyncio.Queue()


# Folder/file name processing
def validateTitle(title):
    r_str = r"[\/\\\:\*\?\"\<\>\|\n]"  # '/ \ : * ? " < > |'
    new_title = re.sub(r_str, "_", title)  # Replace with underscore
    return new_title


# Get album title
async def get_group_caption(message):
    group_caption = ""
    entity = await client.get_entity(message.to_id)
    async for msg in client.iter_messages(entity=entity, reverse=True, offset_id=message.id - 9, limit=10):
        if msg.grouped_id == message.grouped_id:
            if msg.text != "":
                group_caption = msg.text
                return group_caption
    return group_caption


# Get local time
def get_local_time():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


# Judgment similarity rate
def get_equal_rate(str1, str2):
    return difflib.SequenceMatcher(None, str1, str2).quick_ratio()


# Shows File Size
def bytes_to_string(byte_count):
    suffix_index = 0
    while byte_count >= 1024:
        byte_count /= 1024
        suffix_index += 1

    return '{:.2f}{}'.format(
        byte_count, [' bytes', 'KB', 'MB', 'GB', 'TB'][suffix_index]
    )


async def worker(name):
    while True:
        queue_item = await queue.get()
        message = queue_item[0]
        chat_title = queue_item[1]
        entity = queue_item[2]
        file_name = queue_item[3]
        dirname = validateTitle(f'{chat_title}({entity.id})')
        datetime_dir_name = message.date.strftime("%YYear%mMonth")
        file_save_path = os.path.join(save_path, dirname, datetime_dir_name)
        if not os.path.exists(file_save_path):
            os.makedirs(file_save_path)
        # Determine whether the file exists locally
        if file_name in os.listdir(file_save_path):
            os.remove(os.path.join(file_save_path, file_name))
        print(f"{get_local_time()} Download Started： {chat_title} - {file_name}")
        try:
            loop = asyncio.get_event_loop()
            task = loop.create_task(client.download_media(
                message, os.path.join(file_save_path, file_name)))
            await asyncio.wait_for(task, timeout=3600)
            if upload_file_set:
                proc = await asyncio.create_subprocess_exec('gclone',
                                                            '--config=rclone.conf',
                                                            'move',
                                                            os.path.join(
                                                                file_save_path, file_name),
                                                            f"{drive_name}:{{{drive_id}}}/{dirname}/{datetime_dir_name}",
                                                            '--ignore-existing',
                                                            stdout=asyncio.subprocess.DEVNULL)
                await proc.wait()
                if proc.returncode == 0:
                    print(f"{get_local_time()} - {file_name} Download and upload completed")
        except (errors.FileReferenceExpiredError, asyncio.TimeoutError):
            logging.warning(f'{get_local_time()} - {file_name} An exception occurred, try downloading again! ')
            async for new_message in client.iter_messages(entity=entity, offset_id=message.id - 1, reverse=True,
                                                          limit=1):
                await queue.put((new_message, chat_title, entity, file_name))
        except Exception as e:
            print(f"{get_local_time()} - {file_name} {e}")
            await bot.send_message(admin_id, f'Error!\n\n{e}\n\n{file_name}')
        finally:
            queue.task_done()
            # Delete files regardless of whether the upload is successful。
            if upload_file_set:
                try:
                    os.remove(os.path.join(file_save_path, file_name))
                except:
                    pass


@events.register(events.NewMessage(pattern='/start', from_users=admin_id))
async def handler(update):
    text = update.message.text.split(' ')
    if len(text) == 1:
        await bot.send_message(admin_id, 'Wrong format, please input according to the reference format:\n\n '
                                         '<i>/start https://t.me/fkdhlg 0 </i>\n\n'
                                         'Tips: If no offset_id is entered, the download will start from the first one by default。', parse_mode='HTML')
        return
    elif len(text) == 2:
        chat_id = text[1]
        try:
            entity = await client.get_entity(chat_id)
            chat_title = entity.title
            offset_id = 0
            await update.reply(f'Download Started from the first message of {chat_title}。')
        except:
            await update.reply('Chat input error, please enter the link of the channel or group')
            return
    elif len(text) == 3:
        chat_id = text[1]
        offset_id = int(text[2])
        try:
            entity = await client.get_entity(chat_id)
            chat_title = entity.title
            await update.reply(f'Start From {chat_title} First {offset_id} Message。')
        except:
            await update.reply('Chat input error, please enter the link of the channel or group')
            return
    else:
        await bot.send_message(admin_id, 'Parameter error, please input according to the reference format:\n\n '
                                         '<i>/start https://t.me/fkdhlg 0 </i>\n\n'
                                         'Tips:If you do not enter offset_id，Download from the first one by default。', parse_mode='HTML')
        return
    if chat_title:
        print(f'{get_local_time()} - Download Started：{chat_title}({entity.id}) - {offset_id}')
        last_msg_id = 0
        async for message in client.iter_messages(entity, offset_id=offset_id, reverse=True, limit=None):
            if message.media:
                # If it is a group of media
                caption = await get_group_caption(message) if (
                    message.grouped_id and message.text == "") else message.text
                # Filter words such as ads in file names
                if len(filter_list) and caption != "":
                    for filter_keyword in filter_list:
                        caption = caption.replace(filter_keyword, "")
                # If the file name is not an empty string, filter and intercept to avoid errors caused by too long file name
                caption = "" if caption == "" else f'{validateTitle(caption)} - '[
                    :50]
                file_name = ''
                # If it is a file
                if message.document:
                    if message.media.document.mime_type == "image/webp":
                        continue
                    if message.media.document.mime_type == "application/x-tgsticker":
                        continue
                    for i in message.document.attributes:
                        try:
                            file_name = i.file_name
                        except:
                            continue
                    if file_name == '':
                        file_name = f'{message.id} - {caption}.{message.document.mime_type.split("/")[-1]}'
                    else:
                        # If the file name already contains the title, filter the title
                        if get_equal_rate(caption, file_name) > 0.6:
                            caption = ""
                        file_name = f'{message.id} - {caption}{file_name}'
                elif message.photo:
                    file_name = f'{message.id} - {caption}{message.photo.id}.jpg'
                else:
                    continue
                await queue.put((message, chat_title, entity, file_name))
                last_msg_id = message.id
        await bot.send_message(admin_id, f'{chat_title} Download Complete！File ID：{last_msg_id}')


@events.register(events.NewMessage())
async def all_chat_download(update):
    message = update.message
    if message.media:
        chat_id = update.message.to_id
        entity = await client.get_entity(chat_id)
        if entity.id in blacklist:
            return
        chat_title = entity.title
        # If it is a group of media
        caption = await get_group_caption(message) if (
            message.grouped_id and message.text == "") else message.text
        if caption != "":
            for fw in filter_list:
                caption = caption.replace(fw, '')
        # If the file name is not an empty string, filter and intercept to avoid errors caused by too long file name
        caption = "" if caption == "" else f'{validateTitle(caption)} - '[:50]
        file_name = ''
        # If it is a file
        if message.document:
            try:
                if type(message.media) == MessageMediaWebPage:
                    return
                if message.media.document.mime_type == "image/webp":
                    file_name = f'{message.media.document.id}.webp'
                if message.media.document.mime_type == "application/x-tgsticker":
                    file_name = f'{message.media.document.id}.tgs'
                for i in message.document.attributes:
                    try:
                        file_name = i.file_name
                    except:
                        continue
                if file_name == '':
                    file_name = f'{message.id} - {caption}.{message.document.mime_type.split("/")[-1]}'
                else:
                    # If the file name already contains the title, filter the title
                    if get_equal_rate(caption, file_name) > 0.6:
                        caption = ""
                    file_name = f'{message.id} - {caption}{file_name}'
            except:
                print(message.media)
        elif message.photo:
            file_name = f'{message.id} - {caption}{message.photo.id}.jpg'
        else:
            return
        # Filter words such as ads in file names
        for filter_keyword in filter_list:
            file_name = file_name.replace(filter_keyword, "")
        print(chat_title, file_name)
        await queue.put((message, chat_title, entity, file_name))


if __name__ == '__main__':
    bot = TelegramClient('telegram_channel_downloader_bot',
                         api_id, api_hash).start(bot_token=str(bot_token))
    client = TelegramClient(
        'telegram_channel_downloader', api_id, api_hash).start()
    bot.add_event_handler(handler)
    if donwload_all_chat:
      client.add_event_handler(all_chat_download)
    tasks = []
    try:
        for i in range(max_num):
            loop = asyncio.get_event_loop()
            task = loop.create_task(worker(f'worker-{i}'))
            tasks.append(task)
        print('Successfully started (Press Ctrl+C to stop)')
        client.run_until_disconnected()
    finally:
        for task in tasks:
            task.cancel()
        client.disconnect()
        print('Stopped!')
