"""
Telegram Media Transfer - Web UI
Flask web application with real-time progress tracking
"""

from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, FloodWaitError
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
import asyncio
import os
import json
from datetime import datetime
import threading
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'telegram-transfer-secret-key-2024'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global variables
transfer_status = {
    'is_running': False,
    'current': 0,
    'total': 0,
    'success': 0,
    'failed': 0,
    'skipped': 0,
    'message': 'Ready',
    'logged_in': False
}

# API credentials from environment or defaults
API_ID = os.getenv('API_ID', '33864150')
API_HASH = os.getenv('API_HASH', '0938f04741c164281a160dd7099e4025')
PHONE = os.getenv('PHONE', '+94714527083')
SOURCE_CHANNEL = int(os.getenv('SOURCE_CHANNEL', -1003916408757))
TARGET_CHANNEL = int(os.getenv('TARGET_CHANNEL', -1004460843642))

SESSION_DIR = 'session_data'
os.makedirs(SESSION_DIR, exist_ok=True)
SESSION_PATH = os.path.join(SESSION_DIR, 'session')
TRANSFERRED_DB = os.path.join(SESSION_DIR, 'transferred_messages.json')
DOWNLOAD_DIR = 'telegram_downloads'

# Auto-migrate session & DB files from root directory if they exist
if os.path.exists('session.session') and not os.path.exists(SESSION_PATH + '.session'):
    import shutil
    try:
        shutil.copy('session.session', SESSION_PATH + '.session')
    except Exception:
        pass

if os.path.exists('transferred_messages.json') and not os.path.exists(TRANSFERRED_DB):
    import shutil
    try:
        shutil.copy('transferred_messages.json', TRANSFERRED_DB)
    except Exception:
        pass

client = None
client_loop = None


def run_async(coro):
    """Helper to run async functions in sync context"""
    global client_loop
    if client_loop is None:
        client_loop = asyncio.new_event_loop()
        threading.Thread(target=client_loop.run_forever, daemon=True).start()
    return asyncio.run_coroutine_threadsafe(coro, client_loop).result()


def load_transferred_db():
    """Load database of already transferred message IDs"""
    if os.path.exists(TRANSFERRED_DB):
        try:
            with open(TRANSFERRED_DB, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_transferred_db(db):
    """Save database of transferred message IDs"""
    with open(TRANSFERRED_DB, 'w') as f:
        json.dump(db, f, indent=2)


def is_already_transferred(db, source_channel, message_id):
    """Check if message was already transferred"""
    key = f"{source_channel}_{message_id}"
    return key in db


def mark_as_transferred(db, source_channel, message_id):
    """Mark message as transferred"""
    key = f"{source_channel}_{message_id}"
    db[key] = {
        'transferred_at': datetime.now().isoformat(),
        'message_id': message_id
    }
    save_transferred_db(db)


def emit_status(message, current=None, total=None):
    """Emit status update to web UI"""
    global transfer_status
    transfer_status['message'] = message
    if current is not None:
        transfer_status['current'] = current
    if total is not None:
        transfer_status['total'] = total
    socketio.emit('status_update', transfer_status)


async def transfer_media_async():
    """Async function to transfer media"""
    global client, transfer_status
    
    try:
        emit_status('📥 Fetching messages...')
        
        # Get messages
        messages = []
        async for message in client.iter_messages(SOURCE_CHANNEL, limit=None):
            if message.media:
                messages.append(message)
        
        total = len(messages)
        transfer_status['total'] = total
        
        emit_status(f'📊 Found {total} media messages', 0, total)
        
        # Load database
        db = load_transferred_db()
        
        # Check already transferred
        already_transferred = sum(1 for msg in messages if is_already_transferred(db, SOURCE_CHANNEL, msg.id))
        if already_transferred > 0:
            emit_status(f'⏭️ Skipping {already_transferred} already transferred messages')
        
        success = 0
        failed = 0
        skipped = 0
        
        for idx, message in enumerate(messages, 1):
            if not transfer_status['is_running']:
                emit_status('⏸️ Transfer stopped by user')
                break
            
            # Skip if already transferred
            if is_already_transferred(db, SOURCE_CHANNEL, message.id):
                skipped += 1
                transfer_status['skipped'] = skipped
                transfer_status['current'] = idx
                emit_status(f'⏭️ Skipping message {message.id} (already transferred)', idx, total)
                continue
            
            emit_status(f'📥 Downloading message {message.id}...', idx, total)
            
            try:
                # Download media
                if not os.path.exists(DOWNLOAD_DIR):
                    os.makedirs(DOWNLOAD_DIR)
                
                file_path = await client.download_media(message, DOWNLOAD_DIR)
                
                if file_path:
                    emit_status(f'✅ Downloaded: {os.path.basename(file_path)}', idx, total)
                    
                    # Get caption
                    caption = message.message if message.message else None
                    
                    # Check if video
                    is_video = file_path.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', '.m4v'))
                    
                    # Upload
                    emit_status(f'⬆️ Uploading to target channel...', idx, total)
                    
                    await client.send_file(
                        TARGET_CHANNEL,
                        file_path,
                        caption=caption,
                        supports_streaming=is_video,
                        force_document=False
                    )
                    
                    emit_status(f'✅ Uploaded successfully', idx, total)
                    success += 1
                    transfer_status['success'] = success
                    
                    # Mark as transferred
                    mark_as_transferred(db, SOURCE_CHANNEL, message.id)
                    
                    # Delete local file
                    try:
                        os.remove(file_path)
                    except:
                        pass
                    
                    # Delay
                    await asyncio.sleep(3)
                else:
                    failed += 1
                    transfer_status['failed'] = failed
                    
            except FloodWaitError as e:
                emit_status(f'⚠️ FloodWait! Waiting {e.seconds} seconds...', idx, total)
                await asyncio.sleep(e.seconds)
            except Exception as e:
                emit_status(f'❌ Error: {str(e)}', idx, total)
                failed += 1
                transfer_status['failed'] = failed
        
        transfer_status['is_running'] = False
        emit_status(f'✅ Transfer completed! Success: {success}, Failed: {failed}, Skipped: {skipped}', total, total)
        
    except Exception as e:
        transfer_status['is_running'] = False
        emit_status(f'❌ Error: {str(e)}')


def ensure_client():
    """Ensure TelegramClient is instantiated and connected on client_loop"""
    global client
    if client is None:
        client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
        run_async(client.connect())
    return client


def check_login_status():
    """Check if existing session is authorized"""
    global transfer_status
    if not transfer_status['logged_in'] and os.path.exists(SESSION_PATH + '.session'):
        try:
            ensure_client()
            if run_async(client.is_user_authorized()):
                transfer_status['logged_in'] = True
        except Exception:
            pass


def run_transfer():
    """Run transfer on the client loop to prevent event loop mismatch"""
    try:
        ensure_client()
        run_async(transfer_media_async())
    except Exception as e:
        transfer_status['is_running'] = False
        emit_status(f'❌ Error: {str(e)}')


@app.route('/')
def index():
    """Main page"""
    check_login_status()
    return render_template('index.html', 
                         source_channel=SOURCE_CHANNEL,
                         target_channel=TARGET_CHANNEL,
                         logged_in=transfer_status['logged_in'])


@app.route('/api/status')
def get_status():
    """Get current transfer status"""
    check_login_status()
    return jsonify(transfer_status)


@app.route('/api/login', methods=['POST'])
def login():
    """Initialize Telegram client"""
    global client, transfer_status
    
    try:
        def do_login():
            ensure_client()
            is_authorized = run_async(client.is_user_authorized())
            if not is_authorized:
                run_async(client.send_code_request(PHONE))
                return {'status': 'code_sent', 'message': 'Verification code sent to Telegram'}
            else:
                transfer_status['logged_in'] = True
                return {'status': 'logged_in', 'message': 'Already logged in'}
        
        result = do_login()
        return jsonify(result)
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/api/verify', methods=['POST'])
def verify_code():
    """Verify phone code"""
    global client, transfer_status
    
    data = request.get_json()
    code = data.get('code')
    password = data.get('password', '')
    
    try:
        ensure_client()
        
        def do_verify():
            try:
                run_async(client.sign_in(PHONE, code))
                transfer_status['logged_in'] = True
                return {'status': 'success', 'message': 'Login successful'}
            except SessionPasswordNeededError:
                if password:
                    run_async(client.sign_in(password=password))
                    transfer_status['logged_in'] = True
                    return {'status': 'success', 'message': 'Login successful'}
                else:
                    return {'status': 'password_required', 'message': '2FA password required'}
            except PhoneCodeInvalidError:
                return {'status': 'error', 'message': 'Invalid code'}
        
        result = do_verify()
        if result['status'] == 'error':
            return jsonify(result), 400
        return jsonify(result)
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/api/start', methods=['POST'])
def start_transfer():
    """Start media transfer"""
    global transfer_status
    
    if not transfer_status['logged_in']:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 400
    
    if transfer_status['is_running']:
        return jsonify({'status': 'error', 'message': 'Transfer already running'}), 400
    
    transfer_status['is_running'] = True
    transfer_status['current'] = 0
    transfer_status['total'] = 0
    transfer_status['success'] = 0
    transfer_status['failed'] = 0
    transfer_status['skipped'] = 0
    
    # Start transfer in background thread
    thread = threading.Thread(target=run_transfer)
    thread.daemon = True
    thread.start()
    
    return jsonify({'status': 'success', 'message': 'Transfer started'})


@app.route('/api/stop', methods=['POST'])
def stop_transfer():
    """Stop media transfer"""
    global transfer_status
    transfer_status['is_running'] = False
    return jsonify({'status': 'success', 'message': 'Transfer stopping...'})


if __name__ == '__main__':
    # Create directories
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    # Run app on port 3000
    print("🚀 Starting Telegram Media Transfer Web UI on http://0.0.0.0:3000")
    socketio.run(app, host='0.0.0.0', port=3000, debug=False, allow_unsafe_werkzeug=True)
