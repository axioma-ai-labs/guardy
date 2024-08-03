from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import bot.resource_utils as utils
from app import verify_user_command
import bot.config as config
import logging


# bot group start keyboard
def get_start_keyboard(context):

    bot_username = context.bot.username

    return [
        [InlineKeyboardButton(text="➕ Add to a group ➕", url=f"https://t.me/{bot_username}?startgroup=true&admin=change_info+post_messages+edit_messages+delete_messages+restrict_members+pin_messages+manage_chat")],
        [InlineKeyboardButton(text="💬 Commands", callback_data="cmd_cb_setup")],
        [InlineKeyboardButton(text="💡 Features", callback_data="cmd_cb_features"),
         InlineKeyboardButton(text="🆘 Help center", callback_data="cmd_cb_help")],
    ]

# back button
def get_back_button():
    return [[InlineKeyboardButton(text="⬅️ Back", callback_data="cmd_cb_back_to_menu")]]

# close message button
def get_close_button(message_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Close", callback_data=f"cmd_cb_close_{message_id}")]
    ])


########## COMMANDS ##########
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db):

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    payload = context.args[0] if context.args else ""

    try: 

        # check if bot is already an admin
        if await utils.is_bot_admin(update, context, chat_id, display_warning=True):
            return
        
        # check if the user is in db: Works in all cases
        user_id = update.message.from_user.id
        user_exists = db.check_if_user_exists(user_id=user_id)
        if not user_exists:
            db.add_new_private_user(user_id=user_id,
                                    username=update.message.from_user.username,
                                    first_name=update.message.from_user.first_name,
                                    last_name=update.message.from_user.last_name
            )
        
        # if user comes from the group (display verification for the given group on /start)
        if payload == "verify":
            await verify_user_command(update, context)
        
        # classic /start
        else:
            start_keyboard = get_start_keyboard(context)

            start_message = (
                f"🛡️ Welcome to <b>Guardy</b>! 🛡️\n\n"
                f"Guardy is a leading Telegram community assistant with focus on security & seamless management\n\n"
                f"The bot was crafted to fortify your group against ever-evolving annoying bots, scammers & spammers.\n\n"
                f"👥 <b>Top-Tier User Verification</b>: Streamlining the process to distinguish real humans from bots.\n\n"
                f"🎣 <b>Scam & Phishing Prevention</b>: Proactively identifying and removing scam and phishing attempts (e.g. external links, forwarded messages) to protect your community members.\n\n"
                f"🚫 <b>Bot Fighting</b>: Detecting and removing unwanted bot activities ensuring only authorized bots are allowed in the group.\n\n"
                f"Enhance your group's security effortlessly with Guardy in just three simple steps.\n\n"
                f"Safeguarding groups against darkness."
            )
        
            await context.bot.send_message(
                text=start_message,
                chat_id=chat_id,
                reply_markup=InlineKeyboardMarkup(start_keyboard),
                parse_mode=ParseMode.HTML
            )

    except Exception as e:
        print(f"An error occurred in start_command: {e}")
        await context.bot.send_message(chat_id=chat_id, text="An error occurred while processing your request. Please try again.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        if await utils.is_group_or_supergroup(update, context, chat_id, False):
            if not await utils.is_user_admin(update, context, chat_id, user_id, False):
                return
        message = (
            f"🆘 <b>Guardy Help Center</b>\n\n"
            f"Welcome to the Guardy's <b>24/7 Help Center</b>! We're here to assist you anytime, ensuring your groups are secure & your experience is smooth!\n\n"
            f"🔸For general support reach out to @iamspacecreated (Please note: I always try to respond promptly, although there may occasionally be delays due to high query volumes)\n"
            f"🔸Official Community: <a href='https://t.me/guardy_community'>@guardy_community</a>\n"
            f"🔸Visit our FAQ page for quick answers to common queries\n\n"
            f"⚠️ Please note: Guardy's staff <b>CANNOT</b> provide support for issues related to groups (ban, mute, etc.). Please reach out directly to group admins & moderators!\n\n"
            f"Your seamless experience with Guardy is our priority. Reach out to us for any assistance or information."
        )
        back_button = get_back_button()
        markup = InlineKeyboardMarkup(back_button)
        if update.callback_query:
            await update.callback_query.message.edit_text(message, reply_markup=markup, parse_mode=ParseMode.HTML)
        else:
            message = await update.message.reply_text(message, parse_mode=ParseMode.HTML)
            close_button_markup = get_close_button(message.message_id)
            await message.edit_reply_markup(reply_markup=close_button_markup)
    except Exception as e:
        logging.error(f"Error in help_command: {e}")
        await context.bot.send_message(chat_id=chat_id, text="Failed to process help command.")


async def features_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # check if sent in group/supergroup
    if await utils.is_group_or_supergroup(update, context, chat_id, False):
        # check if sent by admin
        if not await utils.is_user_admin(update, context, chat_id, user_id, False):
            return

    message = (
        f"💡 <b>Guardy Features</b>\n\n"

        f"Guardy offers two distinct plans: <u>Free</u> for essential features and <u>Premium</u> for advanced capabilities.\n\n"

        f"<u>FREE</u>:\n"
        f"👥 <b>Top-Tier User Verification</b>: Keep your group genuine & bot-free with <b>Web</b> or <b>CAPTCHA</b> based human verifications.\n"
        f"🚫 <b>Control Bots</b>: Automatically remove unauthorized bots added by users, keeping your group clean and secure.\n"
        f"🔗 <b>Remove URLs</b>: Automatically detect and remove unwanted links shared by users, preventing spam & phishing.\n"
        f"🔄 <b>Remove Forwarded Messages</b>: Keep your group's conversation original and spam-free by removing forwarded messages.\n\n"

        f"<u>PREMIUM</u>:\n"
        f"💬 <b>Intelligent Q&A</b>: Automatically detect and answer unanswered questions in your group, utilizing your business knowledge for interactive engagement.\n"
        f"🛡️ <b>Contextual Scam & Malware Detection</b>: Advanced contextual AI-powered detection of scams and malware, ensuring utmost group safety.\n"
        f"🤚 <b>Community Scam Prevention</b>: First-rate community voting system for scam prevention, leveraging the power of human awareness to minimize spam, scams & phishing.\n"
        f"🆘 <b>Dedicated Support</b>: Get personal dedicated support for any issues or queries in under 24 hours\n"
        f"🎯 <b>Advisory</b>: Expert insights on enhancing Telegram group security & custom AI integrations\n\n"
        
        f"All the <u>free</u> features will always remain free. ALWAYS.\n\n" 
        f"Explore Guardy Premium in our official Guardy community!"
    )
    
    test_premium_button = [InlineKeyboardButton("⚡ Explore Premium ⚡", url="https://t.me/guardy_community")]
    back_button = get_back_button()
    markup = InlineKeyboardMarkup([test_premium_button, *back_button])

    # check if the update is from a callback query
    if update.callback_query:
        await update.callback_query.message.edit_text(message, reply_markup=markup, parse_mode=ParseMode.HTML)
    else:
        message = await update.message.reply_text(message, parse_mode=ParseMode.HTML)
        close_button_markup = get_close_button(message.message_id)
        await message.edit_reply_markup(reply_markup=close_button_markup)


async def show_config_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db):
    """
    Sends a message to the group with details about the group and the bot's rights.
    Restricted to be used only by admins and only in public groups and supergroups.
    Usage:
    Add as a command handler in `main()`: application.add_handler(CommandHandler("config", config_command))
    """
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    try:
        if not await utils.is_group_or_supergroup(update, context, chat_id, True):
            return
        if not await utils.is_user_admin(update, context, chat_id, user_id, True):
            return
        group_config = db.get_admin_config(group_id=chat_id)
        if group_config:
            config_message = (
                "🔧 <b>Group Configuration</b>\n\n"
                f"🔗 <b>Link Removal:</b> {group_config.get('link_removal', 'Not Set')}\n"
                f"🔀 <b>Forwarded Removal:</b> {group_config.get('forwarded_removal', 'Not Set')}\n"
                f"👤 <b>Human Verification:</b> {group_config.get('human_verification', 'Not Set')}\n"
                f"🤖 <b>Bot Removal:</b> {group_config.get('bot_removal', 'Not Set')}\n"
                f"🔊 <b>Antiflood:</b> {group_config.get('antiflood', 'Not Set')}"
            )
            message = await context.bot.send_message(chat_id, config_message, parse_mode=ParseMode.HTML)
            change_settings_btn = InlineKeyboardButton(text="⚙️ Change settings", callback_data="config_setup_security")
            close_btn = InlineKeyboardButton("❌ Close", callback_data=f"cmd_cb_close_{message.message_id}")
            keyboard = [[change_settings_btn], [close_btn]]
            markup = InlineKeyboardMarkup(keyboard)
            await message.edit_reply_markup(reply_markup=markup)
        else:
            message = await context.bot.send_message(chat_id, "No configuration found for this group.", parse_mode=ParseMode.HTML)
            await utils.delete_message_after(context, chat_id, message.message_id, delay_seconds=5)
    except Exception as e:
        logging.error(f"Error in show_config_command: {e}")
        await context.bot.send_message(chat_id=chat_id, text="Failed to process configuration command.")


async def setup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    try:
        if await utils.is_group_or_supergroup(update, context, chat_id, False):
            if not await utils.is_user_admin(update, context, chat_id, user_id, False):
                return
        message = (
            f"💬 <b>Guardy Commands</b>\n\n"
            f"Guardy offers diverse command set, accessible in both <u>private chats</u> and in <u>public groups</u>.\n\n"
            f"⚠️ Note: Certain commands are only accessible to admins in public groups.\n\n"
            f"<u>Private commands</u>:\n"
            f"Available to <b>everyone</b> in a private chat\n"
            f"/start - Quick start guide\n"
            f"/setup - List of all available commands\n"
            f"/examples - Small examples of Guardy's capabilities\n"
            f"/features - List of all Guardy's <b>FREE</b> & <b>PREMIUM</b> features\n"
            f"/help - Access 24/7 help center\n\n"
            f"<u>Group commands (Admins)</u>:\n"
            f"Available only to the <b>group admins</b> inside the groups\n"
            f"/config - Manage & customize group security settings\n"
            f"/disable - Disable Guardy & turn off all group security settings\n"
            f"/enable - Enable Guardy & turn on maximum security settings\n\n"
            f"<u>Group commands (All)</u>:\n"
            f"Available to <b>everyone</b> inside the groups\n"
            f"/adminlist - List all admins in the current chat\n"
            f"/rules - List all rules in the current chat"
        )
        examples_button = [InlineKeyboardButton("📝 Examples", callback_data="cmd_cb_examples")]
        back_button = get_back_button()
        markup = InlineKeyboardMarkup([examples_button, *back_button])
        if update.callback_query:
            await update.callback_query.message.edit_text(message, reply_markup=markup, parse_mode=ParseMode.HTML)
        else:
            message = await update.message.reply_text(message, parse_mode=ParseMode.HTML)
            close_button_markup = get_close_button(message.message_id)
            await message.edit_reply_markup(reply_markup=close_button_markup)
    except Exception as e:
        logging.error(f"Error in setup_command: {e}")
        await context.bot.send_message(chat_id=chat_id, text="Failed to process setup command.")


async def examples_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    try:
        if await utils.is_group_or_supergroup(update, context, chat_id, False):
            if not await utils.is_user_admin(update, context, chat_id, user_id, False):
                return
        message = (
            "📝 *Examples*\n\n"
            "Below is a detailed guide on what you can accomplish with @GuardyShieldBot\\. Explore all features in the official Guardy Community group\\.\n\n"
            "__*FREE*__:\n"
            "1\\. Send any link to the group\\. It will be automatically removed to ensure security and prevent scams/spam\\.\n"
            "__Example__: `www.youtube.com`\n"
            "2\\. Try sneaking an external bot into the group\\. It will be automatically removed\\.\n"
            "3\\. Try forwarding any message from outside the chat and see it disappear before causing any harm\\.\n\n"
            "__*PREMIUM*__:\n"
            "1\\. Imagine you are a scammer & send a malicious message to the group\\. A community voting process will initiate, and democratic community vote decides its fate\\.\n"
            "__Example__: `Congratulations 🎉 You've won $1.000.000 in the Global Lottery. Claim your prize in our Telegram group ASAP!`\n"
            "2\\. Ask anything about Guardy himself via @GuardyShieldBot\n"
            "__Example__: `@GuardyShieldBot who is your main developer?`\n\n"
            "\\We are tirelessly working on new features & functionalities to enhance your communities' security and reduce the presence of annoying bots and scammers\\."
        )
        back_button = get_back_button()
        markup = InlineKeyboardMarkup(back_button)
        if update.callback_query:
            await update.callback_query.message.edit_text(message, reply_markup=markup, parse_mode=ParseMode.MARKDOWN_V2)
        else:
            message = await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN_V2)
            close_button_markup = get_close_button(message.message_id)
            await message.edit_reply_markup(reply_markup=close_button_markup)
    except Exception as e:
        logging.error(f"Error in examples_command: {e}")
        await context.bot.send_message(chat_id=chat_id, text="Failed to process examples command.")


async def disable_guardy_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db):
        
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    group_title = update.effective_chat.title

    try:
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        group_title = update.effective_chat.title
        if not await utils.is_group_or_supergroup(update, context, chat_id, True):
            return
        if not await utils.is_user_admin(update, context, chat_id, user_id, True):
            return
        group_config = db.get_admin_config(group_id=chat_id)
        if group_config:
            disable_message = (
                "🚫 <b>Confirm Disable Guardy</b>\n\n"
                f"Disabling this feature will turn off all security functionalities for <b>{group_title}</b>. Although Guardy will remain an admin in the group, it will stop active monitoring and protection.\n\n"
                f"Use /enable to reactivate maximum security at any time.\n"
                f"Use /config to manage & adjust the security settings manually according to your needs."
            )
            message = await context.bot.send_message(chat_id, disable_message, parse_mode=ParseMode.HTML)
            disable_guardy_btn = InlineKeyboardButton(text="🚫 Disable Guardy", callback_data="config_disable_guardy")
            close_btn = InlineKeyboardButton("❌ Close", callback_data=f"cmd_cb_close_{message.message_id}")
            keyboard = [[disable_guardy_btn], [close_btn]]
            markup = InlineKeyboardMarkup(keyboard)
            await message.edit_reply_markup(reply_markup=markup)
        else:
            message = await context.bot.send_message(chat_id, "No configuration found for this group.", parse_mode=ParseMode.HTML)
            await utils.delete_message_after(context, chat_id, message.message_id, delay_seconds=5)
    except Exception as e:
        logging.error(f"Error in disable_guardy_command: {e}")
        await context.bot.send_message(chat_id=chat_id, text="Failed to disable Guardy.")


async def enable_guardy_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db):

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    group_title = update.effective_chat.title

    try:
        if not await utils.is_group_or_supergroup(update, context, chat_id, True):
            return
        if not await utils.is_user_admin(update, context, chat_id, user_id, True):
            return
        group_config = db.get_admin_config(group_id=chat_id)
        if group_config:
            enable_message = (
                "✅ <b>Confirm Enable Guardy</b>\n\n"
                f"Activating this feature will implement the highest level of security measures for <b>{group_title}</b>.\n\n"
                f"Use /config to manage & adjust the security settings manually at any time."
            )
            message = await context.bot.send_message(chat_id, enable_message, parse_mode=ParseMode.HTML)
            enable_guardy_btn = InlineKeyboardButton(text="✅ Enable Guardy", callback_data="config_enable_guardy")
            close_btn = InlineKeyboardButton("❌ Close", callback_data=f"cmd_cb_close_{message.message_id}")
            keyboard = [[enable_guardy_btn], [close_btn]]
            markup = InlineKeyboardMarkup(keyboard)
            await message.edit_reply_markup(reply_markup=markup)
        else:
            message = await context.bot.send_message(chat_id, "No configuration found for this group.", parse_mode=ParseMode.HTML)
            await utils.delete_message_after(context, chat_id, message.message_id, delay_seconds=5)
    except Exception as e:
        logging.error(f"Error in enable_guardy_command: {e}")
        await context.bot.send_message(chat_id=chat_id, text="Failed to enable Guardy.")


async def admin_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = update.effective_chat.id

    try:
        if not await utils.is_group_or_supergroup(update, context, chat_id, True):
            return
        admins = await context.bot.get_chat_administrators(chat_id)
        admin_usernames = [f"- @{admin.user.username}" for admin in admins if admin.user.username]
        admins_list_str = "\n".join(admin_usernames)
        config_message = (
            f"🧑‍💻 <b>Group Admins in {update.effective_chat.title}</b>\n\n"
            f"Admins:\n{admins_list_str}\n\n"
        )
        message = await context.bot.send_message(chat_id, config_message, parse_mode=ParseMode.HTML)
        await utils.delete_message_after(context, chat_id, message.message_id, delay_seconds=30)
    except Exception as e:
        logging.error(f"Error in admin_list_command: {e}")
        await context.bot.send_message(chat_id=chat_id, text="Failed to retrieve admin list.")


async def rules_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db):
    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title

    try:
        if not await utils.is_group_or_supergroup(update, context, chat_id, True):
            return
        SETTINGS_MAPPING = config.group_settings_mapping['settings_descriptions']
        group_config = db.get_admin_config(group_id=chat_id)

        if group_config['guardy_status'] == "enabled":
            rules_messages = [f"⚖️ <b>{chat_title} Chat Rules</b>\n\n"]
            for setting, value in group_config.items():
                if value == "no":  # skip settings that are "no"
                    continue
                if setting == 'human_verification':
                    key = f"{setting}_{value}" if value != "no" else setting
                else:
                    key = setting
                if key in SETTINGS_MAPPING:
                    rules_messages.append(f"{SETTINGS_MAPPING[key]}\n\n")
            rules_messages.append(f'P.S. Engage with kindness and uphold mutual respect, making <b>{chat_title}</b> welcoming for all.')
            config_message = "".join(rules_messages).strip()
            message = await context.bot.send_message(chat_id, config_message, parse_mode=ParseMode.HTML)
            await utils.delete_message_after(context, chat_id, message.message_id, delay_seconds=30)
        else:
            return
    except Exception as e:
        logging.error(f"Error in rules_list_command: {e}")
        await context.bot.send_message(chat_id=chat_id, text="Failed to process rules command.")



########## CALLBACKQUERYHANDLERS ##########
async def dispatch_direct_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    """
    Handles callback queries from inline buttons in the bot's messages.

    Usage:
    Add as a callback query handler in `main()`: application.add_handler(CallbackQueryHandler(button_callback_handler))
    """
    
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat.id

    try:
        await query.answer()
        data = query.data
        if data == 'cmd_cb_help':
            await help_command(update, context)
        elif data == 'cmd_cb_features':
            await features_command(update, context)
        elif data == 'cmd_cb_setup':
            await setup_command(update, context)
        elif data == 'cmd_cb_examples':
            await examples_command(update, context)
        elif data == "cmd_cb_back_to_menu":
            start_keyboard = get_start_keyboard(context)
            markup = InlineKeyboardMarkup(start_keyboard)
            start_message = (
                f"🛡️ Welcome to <b>Guardy</b>! 🛡️\n\n"
                f"Guardy is a leading Telegram community assistant with focus on security & seamless management\n\n"
                f"The bot was crafted to fortify your group against ever-evolving annoying bots, scammers & spammers.\n\n"
                f"👥 <b>Top-Tier User Verification</b>: Streamlining the process to distinguish real humans from bots.\n\n"
                f"🎣 <b>Scam & Phishing Prevention</b>: Proactively identifying and removing scam and phishing attempts (e.g. external links, forwarded messages) to protect your community members.\n\n"
                f"🚫 <b>Bot Fighting</b>: Detecting and removing unwanted bot activities ensuring only authorized bots are allowed in the group.\n\n"
                f"Enhance your group's security effortlessly with Guardy in just three simple steps.\n\n"
                f"Safeguarding groups against darkness."
            )
            await query.edit_message_text(text=start_message, reply_markup=markup, parse_mode=ParseMode.HTML)
        elif data.startswith("cmd_cb_close"):
            if await utils.is_group_or_supergroup(update, context, chat_id, False):
                if not await utils.is_user_admin(update, context, chat_id, user_id, True):
                    return
            message_id = int(data.split('_')[-1])  # fetch message id from the callback
            await context.bot.delete_message(chat_id=query.message.chat_id, message_id=message_id)
    except Exception as e:
        logging.error(f"Error in dispatch_direct_command: {e}")
        if query:
            await query.message.reply_text("An error occurred while processing your request.")