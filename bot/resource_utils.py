from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions, ChatMember
from telegram.ext import ContextTypes, CallbackContext
import logging
import re
import random
from telegram.constants import ParseMode
import asyncio

# enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# error logging
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f'Update {update} caused error: {context.error}')

# remove weird characters
def remove_sources_from_response(response: str):
    regex_pattern = r"【.*?】"
    cleaned = re.sub(regex_pattern, '', response)
    return cleaned

# update placeholder message
async def update_placeholder_message(chat_id, message_id, placeholders:list, context):
    try:
        while True:
            random_placeholder = random.choice(placeholders)
            await context.bot.edit_message_text(random_placeholder,
                                                chat_id=chat_id, 
                                                message_id=message_id,
                                                parse_mode=ParseMode.HTML)
            await asyncio.sleep(3.5)  # Repeat every 3.5 secs
    except asyncio.CancelledError:
        logger.info("Placeholder update task was cancelled")
    except Exception as e:
        logger.error(f"Error updating placeholder message: {e}")

# check whether bot was mentioned or not
async def is_bot_mentioned(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message
        if message.chat.type == "private":
            return True
        if message.text is not None and ("@" + context.bot.username) in message.text:
            return True
        if message.reply_to_message is not None and message.reply_to_message.from_user.id == context.bot.id:
            return True
    except Exception as e:
        logger.error(f"Failed to check if bot was mentioned: {e}")
    return False

# URL removal
async def remove_url_message(update: Update, context: CallbackContext, db):
    message = update.effective_message
    chat_id = update.effective_chat.id
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    group_config = db.get_admin_config(group_id=chat_id)
    link_removal = group_config.get('link_removal', 'no')
    if link_removal == "no":
        return
    if await is_user_admin(update, context, chat_id, user_id, False):
        logger.info("User is an admin! Allow URLs!")
        return
    if any(entity.type in ["url", "text_link"] for entity in message.entities):
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
            warning_message = f"❗ @{username} posting links is not allowed in this group ❗"
            warning_msg = await context.bot.send_message(chat_id=chat_id, text=warning_message)
            await delete_message_after(context, chat_id, warning_msg.message_id, 5)  # delete after 5 seconds
        except Exception as e:
            logger.error(f"Error removing URL message: {e}")

# forwarded message removal
async def remove_forwarded_message(update: Update, context: CallbackContext, db):
    message = update.effective_message
    chat_id = update.effective_chat.id
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    group_config = db.get_admin_config(group_id=chat_id)
    forwarded_removal = group_config.get('forwarded_removal', 'no')
    if forwarded_removal == "no":
        return
    if await is_user_admin(update, context, chat_id, user_id, False):
        logger.info("User is an admin! Allow forwarded messages!")
        return
    if message.forward_date:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
            warning_message = f"❗ @{username} forwarding messages is not allowed in this group ❗"
            warning_msg = await context.bot.send_message(chat_id=chat_id, text=warning_message)
            await delete_message_after(context, chat_id, warning_msg.message_id, 5)  # delete after 5 seconds
        except Exception as e:
            logger.error(f"Error removing forwarded message: {e}")

# bot removal
async def remove_external_bots(member, update, context, db):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    group_config = db.get_admin_config(group_id=chat_id)
    bot_removal = group_config.get('bot_removal', 'no')
    if bot_removal == "no":
        return
    if await is_user_admin(update, context, chat_id, user_id, False):
        logger.info("User is an admin! Allow external bots!")
        return
    try:
        await context.bot.kick_chat_member(chat_id, member.id)
        username = f"@{member.username}" if member.username else member.first_name
        warning_message = f"❗ {username} adding external bots is not allowed in this group ❗"
        warning_msg = await context.bot.send_message(chat_id, warning_message)
        await delete_message_after(context, chat_id, warning_msg.message_id, 5)  # delete after 5 seconds
    except Exception as e:
        logger.error(f"Error in remove_external_bot: {e}")

# handle edited message
async def edited_message_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.edited_message.chat.type == "private":
        text = "🥲 Unfortunately, message <b>editing</b> is not supported"
        await update.edited_message.reply_text(text, parse_mode=ParseMode.HTML)

# remove service messages from Telegram
async def remove_service_message(update: Update, context: CallbackContext):
    message = update.effective_message
    chat_member_update = update.chat_member
    logger.info(f"CHAT MEMBER UPDATE: {update}")
    if message.new_chat_members or message.left_chat_member or message.new_chat_title:
        try:
            await context.bot.delete_message(chat_id=message.chat_id, message_id=message.message_id)
        except Exception as e:
            logger.error(f"Error deleting service message: {e}")

# delete bot message
async def delete_message_after(context: CallbackContext, chat_id: int, message_id: int, delay_seconds: int = 10):
    await asyncio.sleep(delay_seconds)
    try:
        await context.bot.delete_message(chat_id, message_id)
    except Exception as e:
        logger.error(f"Error in delete_message_after: {e}")

# configuration
async def send_link_removal_config(query):
    keyboard = [
        [InlineKeyboardButton("Yes", callback_data="config_setup_link_removal_yes")],
        [InlineKeyboardButton("No", callback_data="config_setup_link_removal_no")]
    ]
    await query.message.edit_text(
        "🔗 Remove links? \n\n"
        "Guardy will automatically remove external links posted by non-admin members. \n\n"
        "Enabling this feature helps to reduce spam and prevents the spread of phishing links, keeping the group more secure and focused.",
        reply_markup=InlineKeyboardMarkup(keyboard))

async def send_link_antiflood_config(query):
    keyboard = [
        [InlineKeyboardButton("3", callback_data="config_setup_antiflood_3"), 
         InlineKeyboardButton("5", callback_data="config_setup_antiflood_5"),
         InlineKeyboardButton("10", callback_data="config_setup_antiflood_10"),
         InlineKeyboardButton("15", callback_data="config_setup_antiflood_15")],
        [InlineKeyboardButton("No", callback_data="config_setup_antiflood_no")]
    ]
    await query.message.edit_text(
        "🔊 Enable anti-flood? \n\n"
        "Guardy will mute users sending over X messages within 20 seconds, reducing flooding and maintaining group clean & friendly\n\n"
        "Set the trigger for anti-flood by specifying the maximum messages allowed per 20 seconds.\n\n"
        "Example: Set anti-flood trigger after 10 messages in 20 seconds. Default is 10 messages.",
        reply_markup=InlineKeyboardMarkup(keyboard))

async def send_forwarded_msg_removal_config(query):
    keyboard = [
        [InlineKeyboardButton("Yes", callback_data="config_setup_forwarded_removal_yes")],
        [InlineKeyboardButton("No", callback_data="config_setup_forwarded_removal_no")]
    ]
    await query.message.edit_text(
        "🔀 Remove forwarded messages? \n\n"
        "Guardy will automatically remove messages that are forwarded by non-admin members. \n\n"
        "Forwarded messages can be a source of misinformation, spam, or malicious content, as their original source is often unverified. This feature is essential for maintaining the authenticity and integrity of group discussions.",
        reply_markup=InlineKeyboardMarkup(keyboard))

async def send_human_verification_config(query):
    keyboard = [
        [InlineKeyboardButton("Image", callback_data="config_setup_verification_image")],
        [InlineKeyboardButton("Web", callback_data="config_setup_verification_web")],
        [InlineKeyboardButton("No", callback_data="config_setup_verification_no")]
    ]
    await query.message.edit_text(
        "👤 How to verify new members? \n\n"
        "Human verification is crucial to prevent automated bots from joining and spamming the group. It ensures that only real individuals can participate, enhancing the group's security and conversation quality. \n\n"
        "Image = CAPTCHA-based verification \n"
        "Web = Web-based verification (most secure) \n"
        "No = Verification disabled",
        reply_markup=InlineKeyboardMarkup(keyboard))

async def send_bot_removal_config(query):
    keyboard = [
        [InlineKeyboardButton("Yes", callback_data="config_setup_bot_removal_yes")],
        [InlineKeyboardButton("No", callback_data="config_setup_bot_removal_no")]
    ]
    await query.message.edit_text(
        "🤖 Remove bots? \n\n"
        "Guardy will remove all bots that are added by non-admin members. \n\n"
        "Allowing users to add bots can pose a risk, as some bots may spam or phish information from group members. Removing user-added bots helps in maintaining the security and integrity of the group.",
        reply_markup=InlineKeyboardMarkup(keyboard))

# check if called in group/supergroup
async def is_group_or_supergroup(update, context, chat_id, display_warning=True):
    if update.effective_chat.type not in ["group", "supergroup"]:
        if display_warning and update.message:
            warning_msg = await update.message.reply_text(
                "This command can only be used by <b>admins</b> in <b>groups</b> and <b>supergroups</b>!",
                parse_mode=ParseMode.HTML
            )
            await delete_message_after(context, chat_id, warning_msg.message_id)
        return False
    return True

# check if user is an admin
async def is_user_admin(update, context, chat_id, user_id, display_warning=True):
    user_member = await context.bot.get_chat_member(chat_id, user_id)
    if user_member.status not in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
        if display_warning:
            if update.message:
                warning_msg = await update.message.reply_text(
                    "Only <b>admins</b> can use this command!",
                    parse_mode=ParseMode.HTML
                )
                await delete_message_after(context, chat_id, warning_msg.message_id)
            elif update.callback_query:
                await update.callback_query.answer("Only admins can use this command!", show_alert=True)
        return False
    return True

# check if bot is already an admin
async def is_bot_admin(update, context, chat_id, display_warning=True):
    bot_user_id = context.bot.id
    try:
        bot_member = await context.bot.get_chat_member(chat_id, bot_user_id)
        if bot_member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
            if display_warning:
                if update.message:
                    warning_msg = await update.message.reply_text(
                        "Guardy is already an <b>admin</b> in this group!",
                        parse_mode=ParseMode.HTML
                    )
                    await delete_message_after(context, chat_id, warning_msg.message_id)
                elif update.callback_query:
                    await update.callback_query.answer("Guardy is already an admin in this group!", show_alert=True)
            return True
        else:
            return False
    except Exception as e:
        logger.error(f"Error in is_bot_admin: {e}")
        return False

# check if user is verified or not
async def is_user_verified(user_id: int, group_id: int, db):
    verification_data = db.get_verification_data(user_id, group_id)
    if verification_data and not verification_data.get('verified'):
        return True
    return False

# remove service messages from Telegram
async def delete_service_message(update, context):
    try:
        await context.bot.delete_message(update.effective_chat.id, update.message.message_id)
    except Exception as e:
        logger.error(f"Error deleting service message: {e}")
