import os
import requests
import json
import telebot
from msal import PublicClientApplication
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import pyshorteners
from dotenv import load_dotenv
import pytz

# Load environment variables from .env file
load_dotenv()

# Set up credentials from environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GRAPH_CLIENT_ID = os.getenv('GRAPH_CLIENT_ID')
GRAPH_TENANT_ID = os.getenv('GRAPH_TENANT_ID')
TOKEN_FILE = "user_token.txt"  # File to store the access token

# Set up Telegram bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# MSAL public client for device code flow
msal_app = PublicClientApplication(
    GRAPH_CLIENT_ID,
    authority=f"https://login.microsoftonline.com/{GRAPH_TENANT_ID}"
)

# In-memory user sessions
user_sessions = {}

# Save and load token functions
def save_token_to_file(token_data):
    token_data['expires_at'] = (datetime.now() + timedelta(seconds=token_data['expires_in'])).timestamp()
    with open(TOKEN_FILE, "w") as token_file:
        json.dump(token_data, token_file)

def load_token_from_file():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as token_file:
            token_data = json.load(token_file)
            if datetime.now().timestamp() < token_data['expires_at']:
                return token_data
            elif 'refresh_token' in token_data:
                # Token expired, use the refresh token to get a new access token
                new_token_response = msal_app.acquire_token_by_refresh_token(
                    token_data['refresh_token'],
                    scopes=["Files.ReadWrite.All"]
                )
                if "access_token" in new_token_response:
                    save_token_to_file(new_token_response)
                    return new_token_response
    return None

# Authenticate the user with Microsoft Graph using device code flow
def authenticate_user(user_id):
    # Include the offline_access scope to allow for token refresh
    flow = msal_app.initiate_device_flow(scopes=["Files.ReadWrite.All"])

    if 'user_code' not in flow:
        raise ValueError("Failed to create device flow. Check app permissions.")

    bot.send_message(user_id, f"Go to {flow['verification_uri']} and enter the code: {flow['user_code']}")
    token_response = msal_app.acquire_token_by_device_flow(flow)
    
    if "access_token" in token_response:
        save_token_to_file(token_response)
        bot.send_message(user_id, "You have been successfully authenticated!")
    else:
        bot.send_message(user_id, "Authentication failed, please try again.")

# Fetch files from OneDrive
def get_files(access_token, folder_id=None):
    if folder_id:
        url = f"https://graph.microsoft.com/v1.0/me/drive/items/{folder_id}/children"
    else:
        url = "https://graph.microsoft.com/v1.0/me/drive/root/children"
        
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json().get('value', [])
    else:
        print(f"Error fetching files: {response.status_code}")
        return None

# Find a folder by name in a list of files
def find_folder_id_by_name(files, folder_name):
    for file in files:
        if file.get('folder', None) and file['name'] == folder_name:
            return file['id']
    return None

# List files in the "USER MARIO" folder
@bot.message_handler(commands=['myfiles'])
def list_files_command(message, folder_id=None, page=0, edit=False):
    list_files(message, folder_id=folder_id, page=page, edit=edit)

def list_files(message, folder_id=None, page=0, edit=False):
    user_id = message.chat.id
    token_data = load_token_from_file()

    if not token_data or 'access_token' not in token_data:
        bot.send_message(user_id, "You need to authenticate first. Initiating device login...")
        authenticate_user(user_id)
        return

    access_token = token_data['access_token']

    if not folder_id:
        root_files = get_files(access_token)
        folder_69_id = find_folder_id_by_name(root_files, "69")
        if not folder_69_id:
            bot.send_message(user_id, "'69' folder not found.")
            return

        files_in_69 = get_files(access_token, folder_69_id)
        user_mario_folder_id = find_folder_id_by_name(files_in_69, "USER MARIO")
        if not user_mario_folder_id:
            bot.send_message(user_id, "'USER MARIO' folder not found.")
            return

        folder_id = user_mario_folder_id
        user_sessions[user_id] = folder_id  # Update current folder

    else:
        user_sessions[user_id] = folder_id  # Update current folder

    files = get_files(access_token, folder_id)

    if files:
        markup = generate_navigation_buttons(folder_id, page, access_token)

        if edit:
            bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id, text="Your files are listed below:", reply_markup=markup)
        else:
            bot.send_message(user_id, "Your files are listed below:", reply_markup=markup)
    else:
        bot.send_message(user_id, "Failed to retrieve files or folder is empty.")

# Callback handler for inline button presses
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.message.chat.id
    message_id = call.message.message_id
    action, item_id, page = parse_callback_data(call.data)

    token_data = load_token_from_file()

    if not token_data or 'access_token' not in token_data:
        bot.send_message(user_id, "Authentication is required. Please login using /login.")
        return

    access_token = token_data['access_token']

    if action == "folder":
        bot.answer_callback_query(call.id, "Fetching folder contents...")
        list_files(call.message, folder_id=item_id, page=0, edit=True)
    elif action == "file":
        bot.answer_callback_query(call.id, "Generating file link...")
        username = call.from_user.username or "unknown_user"
        generate_file_link(item_id, token_data['access_token'], user_id, username)
    elif action == "navigate":
        bot.answer_callback_query(call.id, "Navigating...")
        markup = generate_navigation_buttons(item_id, int(page), token_data['access_token'])
        bot.edit_message_reply_markup(chat_id=user_id, message_id=message_id, reply_markup=markup)
    elif action == "getalllinks":
        bot.answer_callback_query(call.id, "Generating all file links...")
        username = call.from_user.username or "unknown_user"
        generate_all_file_links(item_id, token_data['access_token'], user_id, username)
    elif action == "home":
        # Retrieve the user's current folder
        current_folder_id = user_sessions.get(user_id)

        # Function to get USER MARIO folder ID
        def get_user_mario_folder_id(access_token):
            root_files = get_files(access_token)
            folder_69_id = find_folder_id_by_name(root_files, "69")
            if not folder_69_id:
                return None

            files_in_69 = get_files(access_token, folder_69_id)
            user_mario_folder_id = find_folder_id_by_name(files_in_69, "USER MARIO")
            return user_mario_folder_id

        user_mario_folder_id = get_user_mario_folder_id(access_token)

        if not user_mario_folder_id:
            bot.answer_callback_query(call.id, "USER MARIO folder not found.")
            return

        if current_folder_id == user_mario_folder_id:
            bot.answer_callback_query(call.id, "You are already in USER MARIO folder.")
            bot.send_message(user_id, "You are already in USER MARIO folder.")
        else:
            bot.answer_callback_query(call.id, "Returning to USER MARIO folder...")
            list_files(call.message, folder_id=None, edit=True)  # Navigates to USER MARIO

# Generate shareable links for all files in a folder
def generate_all_file_links(folder_id, access_token, user_id, username):
    files = get_files(access_token, folder_id)
    if files:
        links = []
        for file in files:
            if not file.get('folder', None):  # Skip folders, only get files
                link = create_share_link(file['id'], access_token, file['name'])
                if link:
                    links.append(f"{file['name']}: {link}")
                    log_file_link(user_id, username, file['name'])  # Log the file link generation
        
        if links:
            bot.send_message(user_id, "\n".join(links))
        else:
            bot.send_message(user_id, "No links found or failed to generate links.")
    else:
        bot.send_message(user_id, "No files found in the folder.")

# Create a shareable link for a specific file
def create_share_link(file_id, access_token, file_name):
    url = f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/permissions"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        permissions = response.json().get('value', [])
        for permission in permissions:
            link = permission.get('link', {}).get('webUrl')
            if link and ':v:' in link:
                clean_link = link.split('?')[0] + "?download=1"
                return shorten_url(clean_link)

    create_link_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/createLink"
    body = {
        'type': 'view',
        'scope': 'anonymous'
    }

    create_link_response = requests.post(create_link_url, headers=headers, json=body)
    
    if create_link_response.status_code == 201:
        link = create_link_response.json().get('link', {}).get('webUrl', None)
        if link and ':v:' in link:
            clean_link = link.split('?')[0] + "?download=1"
            return shorten_url(clean_link)

    return None

# Shorten a URL using TinyURL
def shorten_url(url):
    s = pyshorteners.Shortener()
    return s.tinyurl.short(url)

# Generate a shareable link for a specific file
def generate_file_link(file_id, access_token, user_id, username):
    """Generate a shareable link for a specific file."""
    # Fetch the file metadata (to get the file name)
    url = f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        file_metadata = response.json()
        file_name = file_metadata['name']
        link = create_share_link(file_id, access_token, file_name)
        
        if link:
            bot.send_message(user_id, f"File link for {file_name}: {link}")
            log_file_link(user_id, username, file_name)  # Log the file link generation
        else:
            bot.send_message(user_id, "Failed to generate file link.")
    else:
        bot.send_message(user_id, "Error retrieving file details.")

# Generate navigation buttons for pagination and actions
def generate_navigation_buttons(folder_id, page, access_token):
    files = get_files(access_token, folder_id)
    markup = InlineKeyboardMarkup()

    page_size = 10
    start = page * page_size
    end = start + page_size

    for file in files[start:end]:
        if file.get('folder', None):
            markup.add(InlineKeyboardButton(text=f"📁 {file['name']}", callback_data=f"folder:{file['id']}:0"))
        else:
            markup.add(InlineKeyboardButton(text=f"🗂️ {file['name']}", callback_data=f"file:{file['id']}:0"))

    # Create navigation buttons
    navigation_buttons = []
    if page > 0:
        navigation_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"navigate:{folder_id}:{page-1}"))
    if end < len(files):
        navigation_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"navigate:{folder_id}:{page+1}"))

    # Create home and all links buttons
    home_button = InlineKeyboardButton("Generate All Links 🔗", callback_data=f"getalllinks:{folder_id}:0")
    all_links_button = InlineKeyboardButton("🏠 Home", callback_data=f"home:{folder_id}:0")

    # Add navigation, home, and all links buttons in a single row
    markup.row(*navigation_buttons)
    markup.row(home_button, all_links_button)

    return markup

# Parse callback data for actions
def parse_callback_data(callback_data):
    """Parse callback data into action, item_id, and page."""
    parts = callback_data.split(":")
    if len(parts) == 3:
        return parts[0], parts[1], int(parts[2])
    else:
        return parts[0], parts[1], 0

# Log the generated file link with Indian Standard Time
def log_file_link(user_id, username, file_name):
    ist = pytz.timezone('Asia/Kolkata')
    current_time_ist = datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S')

    log_message = f"User: {username} (ID: {user_id}) generated link for file: {file_name} at {current_time_ist} IST\n"
    with open("link_generation_logs.txt", "a") as log_file:
        log_file.write(log_message)

# Start the bot
if __name__ == "__main__":
    print("Bot is running...")
    bot.polling()
