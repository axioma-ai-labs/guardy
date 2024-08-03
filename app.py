from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ChatMemberHandler, Application
import logging
from database.database import MongoDBManager
import bot.commands as commands
import bot.new_members as n_members 
import bot.verification as verification
import bot.resource_utils as utils
import bot.openai_utils as oai_utils
import bot.group_message_handler as gmh
import bot.config as config
import bot.left_members as l_members


# configuration
CONFIG = config.get_config()
db = MongoDBManager(uri=CONFIG.MONGO_DB_CONNECTION_STRING)


# enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)



# handle new members & groups
async def handle_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_members = update.message.new_chat_members
        group_id = update.message.chat_id
        group_config = db.get_admin_config(group_id=group_id)

        for member in new_members:
            await n_members.handle_bot_as_new_admin(member, update, context, db)
            await n_members.handle_new_group_member(member, update, context, group_id, group_config, CONFIG.GUARDY_URL, db)
            await n_members.handle_external_bots(member, update, context, db, group_id)

        await utils.delete_service_message(update, context)
    except Exception as e:
        logger.error(f"Error in handle_new_members: {e}")


# handle left members & groups
async def handle_left_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    try:
        left_chat_member = update.message.left_chat_member
        message = update.effective_message
        if left_chat_member:
            await context.bot.delete_message(chat_id=message.chat_id, message_id=message.message_id)
    except Exception as e:
        logger.error(f"Error in handle_left_members: {e}")


# user verification
async def handle_user_verification(update, context, query, data):

    user_id = update.effective_user.id
    chat_id = query.message.chat_id
    group_id = context.user_data['to_verify_in_group_id']

    try:
        verif_data = db.get_verification_data(user_id, group_id)
        welcome_message_id = context.user_data.get('welcome_message_id')
        verification_message_id = context.user_data.get('verification_msg_id')
        group_title = verif_data["group_title"]
        group_username = verif_data["group_username"]

        if data == "vrfct_correct_web":
            # verification succeeded | WEB
            db.delete_verification_data(user_id)
            await verification.handle_web_success(query, context, user_id, group_id, chat_id, group_username, group_title, welcome_message_id, verification_message_id)
        elif data == "vrfct_wrong_web":
            # verification failed | WEB
            db.delete_verification_data(user_id)
            await verification.handle_web_failure(query, context, user_id, chat_id, group_id, group_title, welcome_message_id, verification_message_id)
        elif data == "vrfct_correct_captcha":
            # verification succeeded | CAPTCHA
            db.delete_verification_data(user_id)
            await verification.handle_captcha_success(query, context, user_id, group_id, group_title, group_username, chat_id, welcome_message_id)
        elif data == "vrfct_wrong_captcha":
            # verification failed | CAPTCHA
            db.delete_verification_data(user_id)
            await verification.handle_captcha_failure(query, context, user_id, group_id, group_title, chat_id, welcome_message_id)
        elif data == "vrfct_regenerate_captcha":
            # regenerate CAPTCHA
            await verification.regenerate_captcha(update, context)
        else:
            logger.error(f"Unknown verification callback: {data}")

    except Exception as e:
        logger.error(f"Error during user verification for user {user_id} in group {group_id}: {e}")
        await query.answer("An error occurred during the verification process. Please try again.")


# callback handler
async def unified_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        data = query.data
        chat_id = query.message.chat_id
        user_id = query.from_user.id

        if data.startswith("config_full_security") or data.startswith("config_enable_guardy"):
            await verification.set_full_security(db, query, update, user_id, context, chat_id)
        elif data.startswith("config_disable_"):
            await verification.disable_all_functionality(db, query, update, user_id, context, chat_id)
        elif data.startswith("config_setup_"):
            await verification.set_manual_security(db, update, context)
        elif data.startswith("cmd_cb_"):
            await commands.dispatch_direct_command(update, context)
        elif data.startswith("vrfct_"):
            await handle_user_verification(update, context, query, data)
        elif data.startswith("msg_check_vote_"):
            await gmh.dispatch_group_msg_voting(query, update, db)
        else:
            logger.info("TODO: MORE CALLBACKS TO COME!")
    except Exception as e:
        logger.error(f"Error in unified_callback_handler: {e}")
        if query:
            await query.answer("An error occurred, please try again.")



# handle bot query inside groups
async def handle_bot_group_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        group_id = update.message.chat_id

        if not await utils.is_group_or_supergroup(update, context, chat_id):
            return

        PREMIUM_GROUPS = config.premium_groups['premium_groups_id']
        group_config = db.get_admin_config(group_id=group_id)
        antiflood_interval = group_config.get('antiflood', 'no')

        if antiflood_interval != 'no':
            interval = int(antiflood_interval)
            await gmh.antiflood_checker(update, context, interval)

        if chat_id in PREMIUM_GROUPS:
            await gmh.antiflood_checker(update, context, antiflood_interval)
            await gmh.analyse_group_msg_from_user(update, context, db, chat_id)
            await oai_utils.activate_premium_assistance(update, context, chat_id, CONFIG.OPENAI_GUARDY_ASSISTANT_ID, CONFIG.OPENAI_GUARDY_ASSISTANT_API_KEY)
    except Exception as e:
        logger.error(f"Error in handle_bot_group_query: {e}")


# /verify command
async def verify_user_command(update, context):

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    group_id = context.user_data.get('to_verify_in_group_id')

    try:
        # check if there is pending verification
        if not await utils.is_user_verified(user_id, group_id, db):
            return

        # fetch group configuration
        group_config = db.get_admin_config(group_id=group_id)
        if group_config:
            verification_type = group_config.get('human_verification', 'no')

            if verification_type == 'web':
                await verification.web_command(update, context)
            elif verification_type == 'image':
                await verification.captcha_command(update, context)
            elif verification_type == 'no':
                pass  # No action required if no verification type is set
            else:
                logger.error(f"Unexpected verification type: {verification_type} for group: {chat_id}")
        else:
            logger.warning(f"No group configuration found for group: {chat_id}")
    except Exception as e:
        logger.error(f"Error during verification process for user {user_id} in group {chat_id}: {e}")
        await update.message.reply_text("An error occurred during the verification process. Please contact support.")



def main() -> None:

    application = (Application.builder()
                   .token(token=CONFIG.GUARDY_BOT_API_KEY)
                   .concurrent_updates(True)).build()

    # core functionality 1
    application.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.Entity("url"), lambda update, context: utils.remove_url_message(update, context, db)))
    application.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.Entity("text_link"), lambda update, context: utils.remove_url_message(update, context, db)))
    application.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.FORWARDED, lambda update, context: utils.remove_forwarded_message(update, context, db)))

    # commands
    application.add_handler(CommandHandler("start", lambda update, context: commands.start_command(update, context, db)))
    application.add_handler(CommandHandler("config", lambda update, context: commands.show_config_command(update, context, db)))
    application.add_handler(CommandHandler("rules", lambda update, context: commands.rules_list_command(update, context, db)))
    application.add_handler(CommandHandler("enable", lambda update, context: commands.enable_guardy_command(update, context, db)))
    application.add_handler(CommandHandler("disable", lambda update, context: commands.disable_guardy_command(update, context, db)))
    application.add_handler(CommandHandler("help", commands.help_command))
    application.add_handler(CommandHandler("setup", commands.setup_command))
    application.add_handler(CommandHandler("examples", commands.examples_command))
    application.add_handler(CommandHandler("verify", verify_user_command))
    application.add_handler(CommandHandler('features', commands.features_command))
    application.add_handler(CommandHandler('adminlist', commands.admin_list_command))

    # core functionality 2
    application.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.TEXT, handle_bot_group_query))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_members))
    application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, handle_left_members))
    application.add_handler(ChatMemberHandler(lambda update, context: l_members.handle_left_guardy(update, context, db), ChatMemberHandler.MY_CHAT_MEMBER))


    # verification
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, verification.web_app_data)) # web app
    application.add_handler(CallbackQueryHandler(unified_callback_handler))

    # other
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()