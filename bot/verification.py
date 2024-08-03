from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto
from telegram.ext import ContextTypes
import logging
from telegram.constants import ParseMode
from telegram.error import BadRequest

import json
import random
from io import BytesIO
import os

from multicolorcaptcha import CaptchaGenerator
import bot.resource_utils as utils


# Constants
CAPTCHA_SIZE_NUM = 2  # Captcha image size number (2 -> 640x360)
CAPTCHA_DIFFICULTY = 2
RANDOM_OPTION_RANGE = (0, 200)
RANDOM_NUMBERS_COUNT = 4
GUARDY_URL = os.getenv('GUARDY_URL')


# logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


################################### CAPTCHA ###################################

CAPTCHA_SIZE_NUM = 2  # CATPCHA image size (640x360)
CAPTCHA_DIFFICULTY = 2
RANDOM_OPTION_RANGE = (0, 200)
RANDOM_NUMBERS_COUNT = 4


# generate CAPTCHA
def generate_captcha():
    try:
        generator = CaptchaGenerator(CAPTCHA_SIZE_NUM)
        math_captcha = generator.gen_math_captcha_image(difficult_level=CAPTCHA_DIFFICULTY)
        math_image = math_captcha.image
        math_equation_result = math_captcha.equation_result

        # Convert image to a bytes-like object
        image_bytes = BytesIO()
        math_image.save(image_bytes, format='PNG')
        image_bytes.seek(0)

        return image_bytes, math_equation_result
    except Exception as e:
        logger.error(f"Failed to generate CAPTCHA: {e}")
        return None, None

# generate CAPTCHA random options
def generate_random_options(correct_answer: int, range_limits: tuple, count: int):
    try:
        options = set()
        while len(options) < count - 1:
            option = random.randint(*range_limits)
            if option != correct_answer:
                options.add(option)
        options.add(correct_answer)
        return list(options)
    except Exception as e:
        logger.error(f"Failed to generate random options: {e}")
        return []

# markup for CAPTCHA including correct option + regenerate button
def create_captcha_reply_markup(correct_answer: int, include_reg_btn: bool = True):
    try:
        options = generate_random_options(correct_answer, RANDOM_OPTION_RANGE, RANDOM_NUMBERS_COUNT)
        random.shuffle(options)
        
        options_buttons = [[InlineKeyboardButton(str(option), callback_data=f"vrfct_correct_captcha" if option == correct_answer else f"vrfct_wrong_captcha") for option in options]]
        if include_reg_btn:
            regenerate_button = [InlineKeyboardButton("Regenerate 🔁", callback_data="vrfct_regenerate_captcha")]
            options_buttons.append(regenerate_button)

        return InlineKeyboardMarkup(options_buttons)
    except Exception as e:
        logger.error(f"Failed to create CAPTCHA reply markup: {e}")
        return InlineKeyboardMarkup([])

# verification via CAPTCHA command
async def captcha_command(update, context):
    try:
        image, correct_answer = generate_captcha()
        if image is not None and correct_answer is not None:
            reply_markup = create_captcha_reply_markup(correct_answer)
            caption_msg = "🔒 Solve the CAPTCHA below to verify that you're a human. \n\nPlease note: You can regenerate CAPTCHA only 3x times."
            captcha_msg = await update.message.reply_photo(photo=image, caption=caption_msg, reply_markup=reply_markup)

            context.user_data['correct_answer'] = correct_answer
            context.user_data['captcha_msg_id'] = captcha_msg.message_id
        else:
            await update.message.reply_text("Failed to generate CAPTCHA. Please try again later.")
    except Exception as e:
        logger.error(f"Error processing the captcha_command: {e}")
        await update.message.reply_text("An error occurred while processing the CAPTCHA command.")

# verification via CAPTCHA regeneration command
async def regenerate_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data.setdefault("regen_attempts", 0)
        context.user_data["regen_attempts"] += 1

        image, correct_answer = generate_captcha()
        if image is not None and correct_answer is not None:
            reply_markup = create_captcha_reply_markup(correct_answer, include_reg_btn=context.user_data['regen_attempts'] < 3)

            await update.callback_query.edit_message_media(media=InputMediaPhoto(media=image))
            caption_msg = "🔒 Solve the CAPTCHA below to verify that you're a human. \n\nPlease note: You can regenerate CAPTCHA only 3x times."
            await update.callback_query.edit_message_caption(caption=caption_msg, reply_markup=reply_markup)

            context.user_data['correct_answer'] = correct_answer
        else:
            await update.callback_query.answer("Failed to regenerate CAPTCHA. Please try again later.", show_alert=True)
    except Exception as e:
        logger.error(f"Error processing regenerate_captcha: {e}")
        await update.callback_query.answer("An error occurred while regenerating the CAPTCHA.", show_alert=True)


################################### WEB ###################################

# verification command
async def web_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # send verification button
        verification_msg = await update.message.reply_text(
            "🔒 For verification press the menu button below:",
            reply_markup=ReplyKeyboardMarkup.from_button(
                KeyboardButton(
                    text="🔒 Verification 🔒",
                    web_app=WebAppInfo(url="here will be your verification webpage URL")
                ),
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
        context.user_data['verification_msg_id'] = verification_msg.message_id
    except Exception as e:
        logger.error(f"Error in web_command: {e}")
        await update.message.reply_text("Failed to initiate web verification. Please try again.")

# handle incoming WebAppData
async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        data = json.loads(update.effective_message.web_app_data.data)
        logger.info("WEB DATA RECEIVED: ", data)
        correct_number = data['randomNumber']

        random_numbers = set()
        while len(random_numbers) < 3:
            num = random.randint(1, 100)
            if num != correct_number:
                random_numbers.add(num)

        # combine correct_number with the random numbers and shuffle
        options = list(random_numbers) + [correct_number]
        random.shuffle(options)

        keyboard = [[InlineKeyboardButton(str(number), callback_data='vrfct_correct_web' if number == correct_number else 'vrfct_wrong_web')] for number in options]
        reply_markup = InlineKeyboardMarkup(keyboard)

        get_answer_msg = "🔒 Confirm you're human by selecting the correct number that was displayed in the app. \n\nPlease select:"

        await update.message.reply_html(
            text=get_answer_msg,
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error handling WebApp data: {e}")
        await update.message.reply_text("Failed to process web verification data. Please try again.")


################################### SUCCESS & FAILURE ###################################

# web verification successful
async def handle_web_success(query, context, user_id:int, group_id:int, chat_id:int, group_username:str, group_title:str, welcome_message_id:int, verification_message_id:int):
    """
    Handles actions when web verification is successful.
    
    - Deletes the user's verification data from the database.
    - Unrestricts the user, allowing them to send messages in the group.
    - Sends a confirmation message with a link back to the group.
    - Deletes the welcome message and the confirmation message after a delay.

    Args:
    context (CallbackContext): The bot's context.
    query (CallbackQuery): The CallbackQuery instance.
    user_id (int): The ID of the verified user.
    group_id (int): The ID of the group where verification occurred.
    group_username (str): The username of the group.
    group_title (str): The title of the group.
    welcome_message_id (int): The ID of the initial welcome message.
    db (MongoDBManager): The database manager instance.
    """

    await context.bot.restrict_chat_member(group_id, user_id, permissions=ChatPermissions(can_send_messages=True))

    keyboard = [[InlineKeyboardButton("Back to the group", url=f"https://t.me/{group_username}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    final_message = f"✅ <b>VERIFICATION COMPLETE</b> ✅\n\nYou can now chat in the <b>{group_title}</b> group!"
    status_message = await query.edit_message_text(text=final_message, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    # delete welcome message in the group
    if welcome_message_id:
        await context.bot.delete_message(chat_id=group_id, message_id=welcome_message_id)

    # delete menu button
    if verification_message_id:
        await utils.delete_message_after(context, chat_id, verification_message_id, delay_seconds=0)

    # delete status message
    await utils.delete_message_after(context, chat_id, status_message.message_id, delay_seconds=60)


# web verification failed
async def handle_web_failure(query, context, user_id:int, chat_id:int, group_id:int, group_title:str, welcome_message_id:int, verification_message_id:int):
    """
    Handles actions when web verification fails.
    
    - Deletes the user's verification data from the database.
    - Restricts the user, preventing them from sending messages in the group.
    - Sends a failure message.
    - Deletes the welcome message and the failure message after a delay.

    Args:
    context (CallbackContext): The bot's context.
    query (CallbackQuery): The CallbackQuery instance.
    user_id (int): The ID of the user who failed verification.
    group_id (int): The ID of the group where verification occurred.
    group_title (str): The title of the group.
    welcome_message_id (int): The ID of the initial welcome message.
    db (MongoDBManager): The database manager instance.
    """

    await context.bot.restrict_chat_member(group_id, user_id, permissions=ChatPermissions(can_send_messages=False))
    
    final_message = (
        f"❌ <b>VERIFICATION FAILED</b> ❌\n\n"
        f"You cannot chat in the {group_title} group.\n\n"
        f"Please contact the group admins directly or leave the group and try again..."
    )
    
    status_message = await query.edit_message_text(final_message, parse_mode=ParseMode.HTML)

    # delete welcome message in the group
    if welcome_message_id:
        await context.bot.delete_message(chat_id=group_id, message_id=welcome_message_id)

    # delete menu button
    if verification_message_id:
        await utils.delete_message_after(context, chat_id, verification_message_id, delay_seconds=0)

    # delete status message
    await utils.delete_message_after(context, chat_id, status_message.message_id, delay_seconds=60)


# captcha verification successful
async def handle_captcha_success(query, context, user_id:int, group_id:int, group_title:str, group_username:str, chat_id:int, welcome_message_id:int):
    """
    Handles actions when CAPTCHA verification is successful.
    
    - Deletes the user's verification data from the database.
    - Unrestricts the user, allowing them to send messages in the group.
    - Sends a confirmation message with a link back to the group.
    - Deletes the welcome message, CAPTCHA message, and the confirmation message after a delay.

    Args:
    context (CallbackContext): The bot's context.
    query (CallbackQuery): The CallbackQuery instance.
    user_id (int): The ID of the verified user.
    group_id (int): The ID of the group where verification occurred.
    group_username (str): The username of the group.
    group_title (str): The title of the group.
    chat_id (int): The chat ID of the group.
    welcome_message_id (int): The ID of the initial welcome message.
    db (MongoDBManager): The database manager instance.
    """

    captcha_message_id = context.user_data.get('captcha_msg_id')
    await context.bot.restrict_chat_member(group_id, user_id, permissions=ChatPermissions(can_send_messages=True))

    keyboard = [[InlineKeyboardButton("Back to the group", url=f"https://t.me/{group_username}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    final_message = f"✅ <b>VERIFICATION COMPLETE</b> ✅\n\nYou can now chat in the <b>{group_title}</b> group!"
    status_message = await context.bot.send_message(chat_id=chat_id, text=final_message, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    try:
        if welcome_message_id:
            await context.bot.delete_message(chat_id=group_id, message_id=welcome_message_id)
    except BadRequest as e:
        logger.error(f"Error deleting message: {e.message}")

    context.user_data.pop('correct_answer', None)
    context.user_data.pop('captcha_msg_id', None)

    await utils.delete_message_after(context, chat_id, captcha_message_id, delay_seconds=0)
    await utils.delete_message_after(context, chat_id, status_message.message_id, delay_seconds=60)


# captcha verification failed
async def handle_captcha_failure(query, context, user_id:int, group_id:int, group_title:str, chat_id:int, welcome_message_id:int):
    """
    Handles actions when CAPTCHA verification fails.
    
    - Deletes the user's verification data from the database.
    - Restricts the user, preventing them from sending messages in the group.
    - Sends a failure message.
    - Deletes the welcome message, CAPTCHA message, and the failure message after a delay.

    Args:
    context (CallbackContext): The bot's context.
    query (CallbackQuery): The CallbackQuery instance.
    user_id (int): The ID of the user who failed verification.
    group_id (int): The ID of the group where verification occurred.
    group_title (str): The title of the group.
    chat_id (int): The chat ID of the group.
    welcome_message_id (int): The ID of the initial welcome message.
    db (MongoDBManager): The database manager instance.
    """

    captcha_message_id = context.user_data.get('captcha_msg_id')
    await context.bot.restrict_chat_member(group_id, user_id, permissions=ChatPermissions(can_send_messages=False))
    
    final_message = (
        f"❌ <b>VERIFICATION FAILED</b> ❌\n\n"
        f"You cannot chat in the {group_title} group.\n\n"
        f"Please contact the group admins directly or leave the group and try again..."
    )
    
    status_message = await context.bot.send_message(chat_id=chat_id, text=final_message, parse_mode=ParseMode.HTML)

    if welcome_message_id:
        await context.bot.delete_message(chat_id=group_id, message_id=welcome_message_id)

    context.user_data.pop('correct_answer', None)
    context.user_data.pop('captcha_msg_id', None)

    await utils.delete_message_after(context, chat_id, captcha_message_id, delay_seconds=0)
    await utils.delete_message_after(context, chat_id, status_message.message_id, delay_seconds=60)


################################### MANUAL SETUP & FULL SECURITY ###################################


# manual security setup
async def set_manual_security(db, update, context):
    query = update.callback_query
    chat_id = query.message.chat_id
    user_id = update.callback_query.from_user.id
    data = query.data

    # group config dict
    new_config = {'guardy_status': 'enabled'}

    try:
        # skip if non-admin tries to click
        if not await utils.is_user_admin(update, context, chat_id, user_id):
            return

        if data == "config_setup_security":
            await utils.send_link_removal_config(query)
            return

        elif data.startswith("config_setup_link_removal_"):
            choice = "yes" if "yes" in data else "no"
            new_config['link_removal'] = choice
            await utils.send_forwarded_msg_removal_config(query)

        elif data.startswith("config_setup_forwarded_removal_"):
            choice = "yes" if "yes" in data else "no"
            new_config['forwarded_removal'] = choice
            await utils.send_human_verification_config(query)

        elif data.startswith("config_setup_verification_"):
            choice = data.split("_")[-1]  # extract "image", "web", or "no"
            new_config['human_verification'] = choice
            await utils.send_bot_removal_config(query)

        elif data.startswith("config_setup_bot_removal_"):
            choice = data.split("_")[-1]
            new_config['bot_removal'] = choice if choice in ['yes', 'no'] else 'no'  # default to 'no'
            await utils.send_link_antiflood_config(query)

        elif data.startswith("config_setup_antiflood_"):
            choice = data.split("_")[-1]  # "3", "5", "10", "15", or "no"
            if choice == "no":
                new_config['antiflood'] = "no"
            else:
                new_config['antiflood'] = int(choice)

            message = await query.message.edit_text("🛡️ Your group is now under Guardy's protection! 🛡️")
            await utils.delete_message_after(context, chat_id, message.message_id, 5)

        else:
            # handle other cases 
            logger.warning(f"Unexpected data received in set_manual_security: {data}")
            return

        # update group config in db
        db.set_admin_config(chat_id, new_config)
        print(f"Updated Configuration for {chat_id}: {new_config}")
    except Exception as e:
        logger.error(f"Error in set_manual_security: {e}")
        await query.answer("An error occurred while setting security configurations.")


# full security
async def set_full_security(database, query, update, user_id, context, chat_id: int):
    try:
        # skip if non-admin tries to click
        if not await utils.is_user_admin(update, context, chat_id, user_id):
            return

        full_security_config = {
            'guardy_status': 'enabled',
            'link_removal': 'yes',
            'forwarded_removal': 'yes',
            'human_verification': 'web',
            'bot_removal': 'yes',
            'antiflood': '10'
        }
        database.set_admin_config(chat_id, full_security_config)
        message = await query.message.edit_text("🛡️ Guardy enabled maximum security for this group 🛡️")
        await utils.delete_message_after(context, chat_id, message.message_id, delay_seconds=5)
    except Exception as e:
        logger.error(f"Error in set_full_security: {e}")
        await query.answer("An error occurred while enabling full security.")


# disable all Guardy functionality
async def disable_all_functionality(database, query, update, user_id, context, chat_id: int):
    try:
        # skip if non-admin tries to click
        if not await utils.is_user_admin(update, context, chat_id, user_id):
            return

        full_security_config = {
            'guardy_status': 'disabled',
            'link_removal': 'no',
            'forwarded_removal': 'no',
            'human_verification': 'no',
            'bot_removal': 'no',
            'antiflood': 'no'
        }
        database.set_admin_config(chat_id, full_security_config)
        message = await query.message.edit_text("🚫 Guardy is now disabled!")
        await utils.delete_message_after(context, chat_id, message.message_id, delay_seconds=5)
    except Exception as e:
        logger.error(f"Error in disable_all_functionality: {e}")
        await query.answer("An error occurred while disabling all functionalities.")