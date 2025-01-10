from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import ChatPermissions, Message, ChatJoinRequest
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
AUTH_CHAT = int(os.getenv("AUTH_CHAT"))
AUTH_ADMIN = int(os.getenv("AUTH_ADMIN"))
MONGO_URI = os.getenv("MONGO_URI")

bot = Client(
    "approvebot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    parse_mode=ParseMode.MARKDOWN
)

mongo_client = MongoClient(MONGO_URI)
db = mongo_client['approve_bot']
authorized_users = db['authorizeed_users']

@bot.on_chat_join_request()
async def handle_join_request(_, request: ChatJoinRequest):
    chat_id = request.chat.id
    user_id = request.from_user.id

    if chat_id == AUTH_CHAT:
        user_full_name = request.from_user.full_name
        chat_name = request.chat.title

        if authorized_users.find_one({'user_id': user_id}):
            await request.approve()
            print(f"User {user_full_name} is already authorized and has joined {chat_name}.")
            return

        welcome_message = (f"**👋 {user_full_name}, Welcome to {chat_name}!**\n"
                           "━━━━━━━━━━━━━━━━━\n"
                           "To ensure a safe and engaging community for everyone, we require all members to complete their KYC verification.\n\n"
                           "**KYC Verification Form: [Click here](https://forms.gle/xWAJJk722PDGgAfm8)**\n\n"
                           "Once your verification is approved, you'll gain full access to participate in all our group activities—thanks for joining us!\n\n")
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Verification Form", url="https://forms.gle/xWAJJk722PDGgAfm8")]
        ])
        
        try:
            await bot.send_message(chat_id=user_id, text=welcome_message, reply_markup=keyboard)
            await request.approve()

            await bot.restrict_chat_member(chat_id, user_id, permissions=ChatPermissions(all_perms=False))
        except Exception as e:
            print(f"Error handling join request for user {user_id}: {e}")

@bot.on_message(filters.command("auth") & filters.user(AUTH_ADMIN))
async def authorize_user(client, message: Message):
    if len(message.command) < 2:
        await message.reply("**Usage: /auth @username1 @username2 @username3 ...**")
        return

    usernames = message.command[1:]
    response_messages = []

    chat_name = (await bot.get_chat(AUTH_CHAT)).title

    for username in usernames:
        target_user = await client.get_users(username)
        if not target_user:
            response_messages.append(f"**User {username} not found.**")
            continue

        if authorized_users.find_one({'user_id': target_user.id}):
            response_messages.append(f"**[{target_user.first_name}](tg://user?id={target_user.id}) is already authorized.**")
            continue

        try:
            await bot.restrict_chat_member(AUTH_CHAT, target_user.id, permissions=ChatPermissions(all_perms=True))
            authorized_users.insert_one({'user_id': target_user.id})
            approval_message = f"**You are approved in {chat_name}! Now you can participate in all our group activities.**"
            await bot.send_message(target_user.id, approval_message)
            response_messages.append(f"**[{target_user.first_name}](tg://user?id={target_user.id}) is now authorized to send messages.**")

        except Exception as e:
            response_messages.append(f"**Failed to authorize [{target_user.first_name}](tg://user?id={target_user.id}): {e}**")

    await message.reply("\n".join(response_messages))


@bot.on_message(filters.command("unauth") & filters.user(AUTH_ADMIN))
async def unauthorize_user(client, message: Message):
    if len(message.command) < 2:
        await message.reply("**Usage: /unauth @username1 @username2 @username3 ...**")
        return

    usernames = message.command[1:]
    response_messages = []

    chat_name = (await bot.get_chat(AUTH_CHAT)).title

    for username in usernames:
        target_user = await client.get_users(username)
        if not target_user:
            response_messages.append(f"User {username} not found.")
            continue

        if not authorized_users.find_one({'user_id': target_user.id}):
            response_messages.append(f"**[{target_user.first_name}](tg://user?id={target_user.id}) is not currently authorized or already restricted.**")
            continue

        try:
            await bot.restrict_chat_member(AUTH_CHAT, target_user.id, permissions=ChatPermissions(all_perms=False))
            authorized_users.delete_one({'user_id': target_user.id})
            removed_approval_message = "**Your approval has been removed. You are no longer authorized to participate in all group activities.**"
            await bot.send_message(target_user.id, removed_approval_message)
            response_messages.append(f"**[{target_user.first_name}](tg://user?id={target_user.id}) is now restricted and their approval removed.**")
        except Exception as e:
            response_messages.append(f"**Failed to unauthorize [{target_user.first_name}](tg://user?id={target_user.id}): {e}**")

    await message.reply("\n".join(response_messages))

if __name__ == "__main__":
    bot.run()
