"""
Telegram Channel Media Transfer Tool
Transfer media from one Telegram channel to another
"""

from telethon import TelegramClient
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from telethon.errors import FloodWaitError
import asyncio
import os
import json
from datetime import datetime

# API credentials - You need to get these from https://my.telegram.org/apps
API_ID = os.getenv('API_ID', '33864150')
API_HASH = os.getenv('API_HASH', '0938f04741c164281a160dd7099e4025')
PHONE = os.getenv('PHONE', '+94714527083')

# Channel usernames, IDs, or invite links
# Option 1: Username තියෙනවනම්: '@channelname'
# Option 2: Public link: 'https://t.me/channelname' හෝ '@channelname'
# Option 3: Private channel ID: -1001234567890 (number විදියට)
# Option 4: Invite link: 'https://t.me/+ABC123xyz' හෝ channel name එක
SOURCE_CHANNEL = os.getenv('SOURCE_CHANNEL', -1003916408757)  # පැරණි channel එකේ name එක හෝ ID (quotes නැතිව)
TARGET_CHANNEL = os.getenv('TARGET_CHANNEL', -1004460843642)  # නව channel එකේ name එක හෝ ID (quotes නැතිව)

# Convert to int if string number
if isinstance(SOURCE_CHANNEL, str) and SOURCE_CHANNEL.lstrip('-').isdigit():
    SOURCE_CHANNEL = int(SOURCE_CHANNEL)
if isinstance(TARGET_CHANNEL, str) and TARGET_CHANNEL.lstrip('-').isdigit():
    TARGET_CHANNEL = int(TARGET_CHANNEL)

DOWNLOAD_DIR = 'telegram_downloads'

SESSION_DIR = 'session_data'
os.makedirs(SESSION_DIR, exist_ok=True)
SESSION_PATH = os.path.join(SESSION_DIR, 'session')
TRANSFERRED_DB = os.path.join(SESSION_DIR, 'transferred_messages.json')

class TelegramMediaTransfer:
    def __init__(self, api_id, api_hash, phone):
        self.client = TelegramClient(SESSION_PATH, api_id, api_hash)
        self.phone = phone
        self.transferred_messages = self.load_transferred_db()
        
    def load_transferred_db(self):
        """Load database of already transferred message IDs"""
        if os.path.exists(TRANSFERRED_DB):
            try:
                with open(TRANSFERRED_DB, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_transferred_db(self):
        """Save database of transferred message IDs"""
        with open(TRANSFERRED_DB, 'w') as f:
            json.dump(self.transferred_messages, f, indent=2)
    
    def is_already_transferred(self, source_channel, message_id):
        """Check if message was already transferred"""
        key = f"{source_channel}_{message_id}"
        return key in self.transferred_messages
    
    def mark_as_transferred(self, source_channel, message_id):
        """Mark message as transferred"""
        key = f"{source_channel}_{message_id}"
        self.transferred_messages[key] = {
            'transferred_at': datetime.now().isoformat(),
            'message_id': message_id
        }
        self.save_transferred_db()
        
    async def start(self):
        """Start the client and login"""
        await self.client.start(phone=self.phone)
        print("✅ Successfully logged in!")
    
    async def list_dialogs(self):
        """List all your chats/channels to find IDs"""
        print("\n📋 Your Channels and Chats:")
        print("=" * 80)
        async for dialog in self.client.iter_dialogs():
            entity_type = type(dialog.entity).__name__
            print(f"Name: {dialog.name}")
            print(f"ID: {dialog.id}")
            print(f"Type: {entity_type}")
            if hasattr(dialog.entity, 'username') and dialog.entity.username:
                print(f"Username: @{dialog.entity.username}")
            print("-" * 80)
        print("\n💡 Copy the ID or Name of your channels to use in SOURCE_CHANNEL and TARGET_CHANNEL\n")
        
    async def get_channel_messages(self, channel, limit=None, media_only=True):
        """Get messages from a channel"""
        messages = []
        async for message in self.client.iter_messages(channel, limit=limit):
            if media_only:
                if message.media:
                    messages.append(message)
            else:
                messages.append(message)
        return messages
    
    async def download_media(self, message, path=DOWNLOAD_DIR):
        """Download media from a message"""
        if not os.path.exists(path):
            os.makedirs(path)
            
        try:
            file_path = await self.client.download_media(message, path)
            return file_path
        except Exception as e:
            print(f"❌ Error downloading media: {e}")
            return None
    
    async def send_media(self, channel, file_path, caption=None, supports_streaming=True):
        """Send media to a channel with streaming support for videos"""
        max_retries = 3
        retry_count = 0
        
        # Check if it's a video file
        is_video = file_path.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', '.m4v'))
        
        while retry_count < max_retries:
            try:
                # Send with streaming support for videos
                await self.client.send_file(
                    channel,
                    file_path,
                    caption=caption,
                    supports_streaming=supports_streaming if is_video else False,
                    force_document=False  # Send videos as video, not document
                )
                return True
            except FloodWaitError as e:
                wait_time = e.seconds
                print(f"⚠️ FloodWait! Waiting {wait_time} seconds...")
                await asyncio.sleep(wait_time)
                retry_count += 1
            except Exception as e:
                print(f"❌ Error sending media: {e}")
                return False
        
        print(f"❌ Failed after {max_retries} retries")
        return False
    
    async def transfer_media(self, source, target, limit=None, keep_caption=True, delete_after_upload=False, delay=3):
        """Transfer media from source channel to target channel"""
        print(f"📥 Fetching messages from {source}...")
        messages = await self.get_channel_messages(source, limit=limit)
        
        total = len(messages)
        print(f"📊 Found {total} media messages to transfer")
        print(f"⏱️ Delay between uploads: {delay} seconds")
        
        # Check for already transferred messages
        already_transferred = 0
        for msg in messages:
            if self.is_already_transferred(source, msg.id):
                already_transferred += 1
        
        if already_transferred > 0:
            print(f"⏭️ Skipping {already_transferred} already transferred messages")
        
        success_count = 0
        fail_count = 0
        skip_count = 0
        
        for idx, message in enumerate(messages, 1):
            # Skip if already transferred
            if self.is_already_transferred(source, message.id):
                skip_count += 1
                print(f"\n[{idx}/{total}] ⏭️ Skipping message {message.id} (already transferred)")
                continue
                
            print(f"\n[{idx}/{total}] Processing message {message.id}...")
            
            # Download media
            file_path = await self.download_media(message)
            
            if file_path:
                print(f"✅ Downloaded: {os.path.basename(file_path)}")
                
                # Get caption
                caption = message.message if keep_caption else None
                
                # Upload to target channel
                if await self.send_media(target, file_path, caption):
                    print(f"✅ Uploaded to {target}")
                    success_count += 1
                    
                    # Mark as transferred
                    self.mark_as_transferred(source, message.id)
                    print(f"✅ Marked message {message.id} as transferred")
                    
                    # Delete downloaded file if requested
                    if delete_after_upload:
                        try:
                            os.remove(file_path)
                            print(f"🗑️ Deleted local file")
                        except:
                            pass
                else:
                    fail_count += 1
                    
                # Delay to avoid rate limits
                await asyncio.sleep(delay)
            else:
                fail_count += 1
        
        print(f"\n{'='*50}")
        print(f"✅ Transfer completed!")
        print(f"📊 Success: {success_count}/{total}")
        print(f"⏭️ Skipped: {skip_count}/{total} (already transferred)")
        print(f"❌ Failed: {fail_count}/{total}")
        print(f"{'='*50}")
    
    async def stop(self):
        """Disconnect the client"""
        await self.client.disconnect()


async def main():
    # Initialize the transfer tool
    transfer = TelegramMediaTransfer(API_ID, API_HASH, PHONE)
    
    try:
        # Start client
        await transfer.start()
        
        # Transfer media
        # limit=None means all messages, set a number to limit
        # keep_caption=True will preserve original captions
        # delete_after_upload=True will delete downloaded files after upload
        # delay=3 means 3 seconds between uploads (increase if FloodWait errors occur)
        await transfer.transfer_media(
            source=SOURCE_CHANNEL,
            target=TARGET_CHANNEL,
            limit=None,              # None for all messages, or set a number like 100
            keep_caption=True,       # Keep original captions
            delete_after_upload=True,  # Delete local files after upload to save space
            delay=3                  # Seconds between uploads (recommended: 3-5)
        )
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await transfer.stop()


if __name__ == '__main__':
    asyncio.run(main())
