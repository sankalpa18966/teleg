"""
Telegram Batch Media Downloader with Link Range
Download media from private channels using message links and upload as batches
"""

from telethon import TelegramClient
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from telethon.errors import FloodWaitError
import asyncio
import os
import json
from datetime import datetime
import re

# API credentials
API_ID = os.getenv('API_ID', '33864150')
API_HASH = os.getenv('API_HASH', '0938f04741c164281a160dd7099e4025')
PHONE = os.getenv('PHONE', '+94714527083')

# Target channel to upload batches
TARGET_CHANNEL = os.getenv('TARGET_CHANNEL', -1004460843642)

DOWNLOAD_DIR = os.path.abspath('telegram_downloads')
SESSION_DIR = 'session_data'
os.makedirs(SESSION_DIR, exist_ok=True)
SESSION_PATH = os.path.join(SESSION_DIR, 'session')

# Batch settings
MAX_BATCH_SIZE_GB = 6  # Maximum batch size in GB
MAX_BATCH_SIZE_BYTES = MAX_BATCH_SIZE_GB * 1024 * 1024 * 1024


class TelegramBatchDownloader:
    def __init__(self, api_id, api_hash, phone):
        self.client = TelegramClient(SESSION_PATH, api_id, api_hash)
        self.phone = phone
        
    async def start(self):
        """Start the client and login"""
        await self.client.start(phone=self.phone)
        print("✅ Successfully logged in!")
    
    def parse_message_link(self, link):
        """
        Parse Telegram message link to extract channel ID and message ID
        Supports:
        - https://t.me/c/1234567890/123 (private channel)
        - https://t.me/channelname/123 (public channel)
        """
        # Private channel pattern: https://t.me/c/CHANNEL_ID/MESSAGE_ID
        private_pattern = r'https?://t\.me/c/(\d+)/(\d+)'
        # Public channel pattern: https://t.me/USERNAME/MESSAGE_ID
        public_pattern = r'https?://t\.me/([^/]+)/(\d+)'
        
        private_match = re.match(private_pattern, link)
        if private_match:
            channel_id = int(private_match.group(1))
            message_id = int(private_match.group(2))
            # Convert to proper channel ID format (-100 prefix)
            channel_id = int(f"-100{channel_id}")
            return channel_id, message_id
        
        public_match = re.match(public_pattern, link)
        if public_match:
            username = public_match.group(1)
            message_id = int(public_match.group(2))
            return username, message_id
        
        raise ValueError(f"Invalid Telegram link format: {link}")
    
    async def download_media_from_link(self, link, download_path):
        """Download media from a specific message link"""
        try:
            channel_id, message_id = self.parse_message_link(link)
            
            # Get the specific message
            message = await self.client.get_messages(channel_id, ids=message_id)
            
            if not message or not message.media:
                print(f"⚠️ No media found in message: {link}")
                return None
            
            # Download the media
            file_path = await self.client.download_media(message, download_path)
            
            if file_path:
                file_size = os.path.getsize(file_path)
                print(f"✅ Downloaded: {os.path.basename(file_path)} ({self.format_size(file_size)})")
                return {
                    'path': file_path,
                    'size': file_size,
                    'caption': message.message if message.message else None,
                    'link': link
                }
            return None
            
        except Exception as e:
            print(f"❌ Error downloading from {link}: {e}")
            return None
    
    async def download_media_range(self, base_link, start_id, end_id, download_path=DOWNLOAD_DIR):
        """
        Download media from a range of message IDs
        Example: base_link = "https://t.me/c/1234567890/", start_id = 1, end_id = 50
        """
        if not os.path.exists(download_path):
            os.makedirs(download_path)
        
        downloaded_files = []
        total = end_id - start_id + 1
        
        print(f"\n📥 Starting download of {total} messages...")
        print(f"Range: {start_id} to {end_id}")
        print("=" * 60)
        
        for msg_id in range(start_id, end_id + 1):
            link = f"{base_link.rstrip('/')}/{msg_id}"
            print(f"\n[{msg_id - start_id + 1}/{total}] Processing: {link}")
            
            result = await self.download_media_from_link(link, download_path)
            if result:
                downloaded_files.append(result)
            
            # Small delay to avoid rate limits
            await asyncio.sleep(1)
        
        return downloaded_files
    
    def create_batches(self, files, max_size_bytes=MAX_BATCH_SIZE_BYTES):
        """Group files into batches based on size limit"""
        batches = []
        current_batch = []
        current_size = 0
        
        for file_info in files:
            file_size = file_info['size']
            
            # If single file exceeds limit, put it in its own batch
            if file_size > max_size_bytes:
                if current_batch:
                    batches.append(current_batch)
                    current_batch = []
                    current_size = 0
                batches.append([file_info])
                print(f"⚠️ File {os.path.basename(file_info['path'])} exceeds {MAX_BATCH_SIZE_GB}GB limit")
                continue
            
            # If adding this file would exceed limit, start new batch
            if current_size + file_size > max_size_bytes:
                batches.append(current_batch)
                current_batch = [file_info]
                current_size = file_size
            else:
                current_batch.append(file_info)
                current_size += file_size
        
        # Add remaining files
        if current_batch:
            batches.append(current_batch)
        
        return batches
    
    async def upload_batch(self, batch, target_channel, batch_number, total_batches):
        """Upload a batch of files as a media group"""
        print(f"\n📤 Uploading Batch {batch_number}/{total_batches}")
        print(f"Files in batch: {len(batch)}")
        
        total_size = sum(f['size'] for f in batch)
        print(f"Total size: {self.format_size(total_size)}")
        print("=" * 60)
        
        try:
            if not batch:
                return True
                
            total_files = len(batch)
            uploaded_count = 0
            
            for idx, file_info in enumerate(batch, 1):
                file_path = os.path.abspath(file_info['path'])
                if not os.path.exists(file_path):
                    print(f"⚠️ File missing on disk: {os.path.basename(file_path)}")
                    continue
                    
                file_name = os.path.basename(file_path)
                print(f"  [{idx}/{total_files}] Uploading: {file_name}...")
                
                sent = False
                retries = 0
                while not sent and retries < 3:
                    try:
                        is_vid = file_path.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', '.m4v'))
                        await self.client.send_file(
                            target_channel,
                            file_path,
                            caption=None,
                            supports_streaming=is_vid
                        )
                        sent = True
                        uploaded_count += 1
                        print(f"  ✅ [{idx}/{total_files}] Uploaded: {file_name}")
                        await asyncio.sleep(1.5)
                    except FloodWaitError as e:
                        print(f"⚠️ FloodWait! Waiting {e.seconds} seconds...")
                        await asyncio.sleep(e.seconds + 2)
                        retries += 1
                    except Exception as e:
                        print(f"❌ Error uploading {file_name}: {e}")
                        retries += 1
                        await asyncio.sleep(2)
            
            print(f"✅ Batch {batch_number} completed ({uploaded_count}/{total_files} files uploaded)!")
            return uploaded_count > 0
            
        except FloodWaitError as e:
            wait_time = e.seconds
            print(f"⚠️ FloodWait! Waiting {wait_time} seconds...")
            await asyncio.sleep(wait_time + 1)
            return await self.upload_batch(batch, target_channel, batch_number, total_batches)
        except Exception as e:
            print(f"❌ Error uploading batch {batch_number}: {e}")
            return False
    
    async def process_link_range(self, base_link, start_id, end_id, target_channel, delete_after_upload=True):
        """Main process: download range and upload as batches"""
        print("\n" + "=" * 60)
        print("🚀 Telegram Batch Downloader")
        print("=" * 60)
        
        # Download all files
        downloaded_files = await self.download_media_range(base_link, start_id, end_id)
        
        if not downloaded_files:
            print("\n❌ No files were downloaded!")
            return
        
        print(f"\n✅ Successfully downloaded {len(downloaded_files)} files")
        total_size = sum(f['size'] for f in downloaded_files)
        print(f"Total size: {self.format_size(total_size)}")
        
        # Create batches
        print(f"\n📦 Creating batches (Max {MAX_BATCH_SIZE_GB}GB per batch)...")
        batches = self.create_batches(downloaded_files)
        print(f"✅ Created {len(batches)} batch(es)")
        
        # Display batch info
        for idx, batch in enumerate(batches, 1):
            batch_size = sum(f['size'] for f in batch)
            print(f"  Batch {idx}: {len(batch)} files, {self.format_size(batch_size)}")
        
        # Upload each batch
        print(f"\n📤 Starting upload to channel {target_channel}...")
        success_count = 0
        
        for idx, batch in enumerate(batches, 1):
            if await self.upload_batch(batch, target_channel, idx, len(batches)):
                success_count += 1
            
            # Delay between batches
            if idx < len(batches):
                print(f"\n⏳ Waiting 5 seconds before next batch...")
                await asyncio.sleep(5)
        
        # Cleanup
        if delete_after_upload:
            print("\n🗑️ Cleaning up downloaded files...")
            for file_info in downloaded_files:
                try:
                    os.remove(file_info['path'])
                    print(f"  Deleted: {os.path.basename(file_info['path'])}")
                except Exception as e:
                    print(f"  ⚠️ Could not delete {file_info['path']}: {e}")
        
        # Summary
        print("\n" + "=" * 60)
        print("✅ Process completed!")
        print(f"Downloaded: {len(downloaded_files)} files")
        print(f"Uploaded: {success_count}/{len(batches)} batches")
        print("=" * 60)
    
    def format_size(self, bytes_size):
        """Format bytes to human readable size"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.2f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.2f} TB"
    
    async def stop(self):
        """Disconnect the client"""
        await self.client.disconnect()


async def main():
    # Initialize downloader
    downloader = TelegramBatchDownloader(API_ID, API_HASH, PHONE)
    
    try:
        await downloader.start()
        
        # === මෙතන ඔයාගේ settings දාන්න ===
        
        # Private channel link format: https://t.me/c/CHANNEL_ID/
        # Public channel link format: https://t.me/channelname/
        base_link = "https://t.me/c/3916408757/"  # ඔයාගේ source channel link එක
        
        # Message ID range
        start_id = 1      # පළමු message ID
        end_id = 50       # අවසාන message ID
        
        # Target channel to upload batches
        target = TARGET_CHANNEL  # හෝ channel username "@channelname"
        
        # Delete downloaded files after upload (True/False)
        delete_after = True
        
        # === Process ===
        await downloader.process_link_range(
            base_link=base_link,
            start_id=start_id,
            end_id=end_id,
            target_channel=target,
            delete_after_upload=delete_after
        )
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await downloader.stop()


if __name__ == '__main__':
    # Example usage:
    print("""
    📋 Usage Examples:
    
    1. Private Channel:
       base_link = "https://t.me/c/1234567890/"
       start_id = 1
       end_id = 50
    
    2. Public Channel:
       base_link = "https://t.me/channelname/"
       start_id = 100
       end_id = 150
    
    ⚙️ Edit the settings in main() function and run!
    """)
    
    asyncio.run(main())
