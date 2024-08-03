import logging
import bot.resource_utils as utils
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.constants import ParseMode

# enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# adding new bots by users
async def handle_external_bots(member, update, context, db, chat_id):
    # check if the member is a bot and not the bot itself
    if member.is_bot and member.id != context.bot.id:
        try:
            bot_removal = db.get_admin_config(group_id=chat_id).get('bot_removal', 'no')
            # if bot removal is enabled, kick the bot and send a warning message
            if bot_removal == "yes":
                await context.bot.kick_chat_member(chat_id, member.id)
                warning_message = "Adding external bots is not allowed in this group."
                await context.bot.send_message(chat_id, warning_message)
        except Exception as e:
            logger.error(f"Error in handle_external_bots: {e}")

# configuration of guardy after adding
async def handle_bot_as_new_admin(member, update, context, db):
    # check if the bot itself is added as an admin
    if member.username == context.bot.username:
        try:
            group_id = update.effective_chat.id
            group_exists = db.check_if_group_exists(group_id)
            # if the group doesn't exist in the db, add it
            if not group_exists:
                chat = await context.bot.get_chat(group_id)
                member_count = await chat.get_member_count()
                db.add_new_public_group(
                    group_id=group_id,
                    added_by=update.effective_user.id,
                    member_count=member_count,
                    chat_title=update.effective_chat.title,
                    chat_username=update.effective_chat.username,
                    chat_type=update.effective_chat.type
                )
                logger.info(f"Bot was added to a new public group: {group_id}")

                keyboard = [
                    [InlineKeyboardButton("🛡️ Full Security 🛡️", callback_data="config_full_security")],
                    [InlineKeyboardButton("Manual Configuration", callback_data="config_setup_security")]
                ]
                setup_message = (
                    "Welcome to Guardy - leading Telegram community assistant with focus on security & seamless group management\n\n"
                    "To get started, choose one of the options below:\n\n"
                    "<b>🛡️ Full Security 🛡️</b>: Automatically apply the best security practices in your community (default).\n\n"
                    "<b>Manual Configuration</b>: Manually customize your group's security settings to suit your unique requirements\n\n"
                    "Admins always can adjust the group's security settings using /config command in this group"
                )
                await context.bot.send_message(group_id, setup_message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Error in handle_bot_as_new_admin: {e}")

# new member joins the group
async def handle_new_group_member(member, update, context, group_id, group_config, GUARDY_URL, db):
    # handle only non-bot members
    if not member.is_bot:
        try:
            verification_type = group_config.get('human_verification', 'no')
            # proceed only if verification is required
            if verification_type != "no":
                username = '@' + member.username if member.username else member.first_name
                welcome_message = await context.bot.send_message(
                    chat_id=group_id,
                    text=f"Welcome {username}! Please verify yourself!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Verify me", url=GUARDY_URL + "?start=verify")]
                    ])
                )
                welcome_message_id = welcome_message.message_id
                user_id = member.id

                context.user_data['welcome_message_id'] = welcome_message_id
                context.user_data['to_verify_in_group_id'] = group_id

                db.store_verification_data(
                    group_id=group_id,
                    group_username=update.message.chat.username,
                    group_title=update.message.chat.title,
                    welcome_message_id=welcome_message_id,
                    user_id=user_id,
                    verification_type=verification_type,
                    verified=False
                )
                # restrict the new member from sending messages until they are verified
                await context.bot.restrict_chat_member(group_id, member.id, permissions=ChatPermissions(can_send_messages=False))
        except Exception as e:
            logger.error(f"Error during new group member handling: {e}")
        else:
            username = '@' + member.username if member.username else member.first_name
            welcome_message = await context.bot.send_message(chat_id=group_id, text=f"Welcome {username}!")
            await utils.delete_message_after(context, group_id, welcome_message.message_id)