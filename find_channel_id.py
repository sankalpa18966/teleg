"""
Telegram Channel ID Finder
මේක run කරොත් ඔබේ සියලුම channels list වෙයි IDs සමඟ
"""

from telethon import TelegramClient
import asyncio

# API credentials - telegram_media_transfer.py එකේ දාපු credentials මෙහෙත් දාන්න
API_ID = '33864150'
API_HASH = '0938f04741c164281a160dd7099e4025'
PHONE = '+94714527083'


async def find_channels():
    client = TelegramClient('session', API_ID, API_HASH)
    
    await client.start(phone=PHONE)
    print("✅ Successfully logged in!\n")
    
    print("=" * 100)
    print("📋 YOUR CHANNELS AND GROUPS:")
    print("=" * 100)
    
    channels = []
    groups = []
    chats = []
    
    async for dialog in client.iter_dialogs():
        entity_type = type(dialog.entity).__name__
        
        info = {
            'name': dialog.name,
            'id': dialog.id,
            'type': entity_type,
            'username': None
        }
        
        if hasattr(dialog.entity, 'username') and dialog.entity.username:
            info['username'] = f"@{dialog.entity.username}"
        
        if entity_type == 'Channel':
            if hasattr(dialog.entity, 'broadcast') and dialog.entity.broadcast:
                channels.append(info)
            else:
                groups.append(info)
        else:
            chats.append(info)
    
    # Display Channels
    if channels:
        print("\n📢 CHANNELS:")
        print("-" * 100)
        for idx, ch in enumerate(channels, 1):
            print(f"{idx}. Name: {ch['name']}")
            print(f"   ID: {ch['id']}")
            if ch['username']:
                print(f"   Username: {ch['username']}")
                print(f"   Link: https://t.me/{ch['username'][1:]}")
            else:
                print(f"   🔒 Private Channel (no username)")
            print()
    
    # Display Groups
    if groups:
        print("\n👥 GROUPS/SUPERGROUPS:")
        print("-" * 100)
        for idx, grp in enumerate(groups, 1):
            print(f"{idx}. Name: {grp['name']}")
            print(f"   ID: {grp['id']}")
            if grp['username']:
                print(f"   Username: {grp['username']}")
            print()
    
    print("\n" + "=" * 100)
    print("💡 HOW TO USE:")
    print("=" * 100)
    print("1. Copy the 'Name' හෝ 'ID' of your source channel (පැරණි එක)")
    print("2. Copy the 'Name' හෝ 'ID' of your target channel (නව එක)")
    print("3. telegram_media_transfer.py එකේ SOURCE_CHANNEL සහ TARGET_CHANNEL වලට paste කරන්න")
    print("\nExample:")
    print('   SOURCE_CHANNEL = "My Old Channel"  # Name use කරනවනම්')
    print('   SOURCE_CHANNEL = -1001234567890    # ID use කරනවනම් (number විදියට)')
    print('   SOURCE_CHANNEL = "@channelname"    # Username තියෙනවනම්')
    print("=" * 100)
    
    await client.disconnect()


if __name__ == '__main__':
    print("\n🔍 Finding your Telegram channels...\n")
    asyncio.run(find_channels())
