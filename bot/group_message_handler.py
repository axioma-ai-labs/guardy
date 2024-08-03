from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.constants import ParseMode, ReactionEmoji
import bot.resource_utils as utils
import asyncio
import logging
from scam_algo_src.otis_spam_model import analyze_message
from datetime import datetime, timedelta

# analyse group message
async def analyse_group_msg_from_user(update, context, db, chat_id:int):
    try:
        message = update.message.text
        message_id = update.message.id
        chat_id = update.effective_chat.id

        # calculate scam score
        analysis_result = analyze_message(input_text=message)
        
        if analysis_result['label'] == "spam" and analysis_result['probability'] > 0.6:
            keyboard = [
                [InlineKeyboardButton("Yes", callback_data='msg_check_vote_scam_yes'),
                 InlineKeyboardButton("No", callback_data='msg_check_vote_scam_no')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            scam_alert_message = (
                f"⚠️ <b>SCAM ALERT:</b> Does this message seem suspicious to you? \n\nScam Likelihood: {analysis_result['probability']:.1%}"
            )
            alert_message = await update.message.reply_text(text=scam_alert_message, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
            await update.message.set_reaction(reaction=ReactionEmoji.EYES) # set reaction to potential scam message

            # initialize in db
            db.initialize_scam_voting(group_id=chat_id, scam_message_id=message_id, alert_message_id=alert_message.message_id)
            logging.info(f"Scam message with {message_id} ID initialized in DB!")

            await asyncio.sleep(60) # 1 minute
            await conclude_voting(context, chat_id, db, message_id)
        else:
            return # break if not spam
    except Exception as e:
        logging.error(f"Error during scam analysis: {e}")
        await context.bot.send_message(chat_id, "An error occurred during scam analysis.")

# conclude voting
async def conclude_voting(context, chat_id, db, scam_message_id):
    try:
        voting_record = db.delete_scam_voting(chat_id, scam_message_id)
        alert_message_id = voting_record['alert_message_id']
        thanks_text = ""

        if voting_record:
            total_votes = voting_record['vote_scam_yes'] + voting_record['vote_scam_no']

            if total_votes > 0:
                yes_percentage = (voting_record['vote_scam_yes'] / total_votes) * 100
                no_percentage = (voting_record['vote_scam_no'] / total_votes) * 100

                if voting_record['vote_scam_yes'] > voting_record['vote_scam_no']:
                    thanks_text = f"🛡️ {yes_percentage:.0f}% of voters found this message as a scam. Thanks for keeping the community secure! 🛡️"
                    await utils.delete_message_after(context, chat_id=chat_id, message_id=scam_message_id, delay_seconds=0) # delete scam
                elif voting_record['vote_scam_yes'] < voting_record['vote_scam_no']:
                    thanks_text = f"🛡️ {no_percentage:.0f}% found this message NOT to be a scam. Thanks for staying aware! 🛡️"
                else:
                    thanks_text = "Voting concluded. Action taken based on community decision."
                    await utils.delete_message_after(context, chat_id, alert_message_id, 0)

                # edit alert_message
                thanks_msg = await context.bot.edit_message_text(chat_id=chat_id, message_id=alert_message_id, text=thanks_text)
                await utils.delete_message_after(context, chat_id, thanks_msg.message_id, 10)
            else:
                await utils.delete_message_after(context, chat_id, alert_message_id, 0)
    except Exception as e:
        logging.error(f"Error during voting conclusion: {e}")
        await context.bot.send_message(chat_id, "Failed to conclude voting.")

# dispatch voting (yes/no)
async def dispatch_group_msg_voting(query, update, db):
    try:
        data = query.data
        user_id = query.from_user.id
        chat_id = update.callback_query.message.chat.id
        scam_message_id = query.message.message_thread_id # get scam_message_id from thread
        
        # check if user has voted or not
        if db.check_if_user_voted(chat_id, scam_message_id, user_id):
            logging.info(f"USER {user_id} ALREADY VOTED!")
            await query.answer("You've already voted!", show_alert=True)
            return

        db.add_voter(chat_id, scam_message_id, user_id)
        logging.info(f"USER VOTED: {user_id}")
        
        # count vote Yes
        if data == 'msg_check_vote_scam_yes':
            db.update_scam_voting(chat_id, scam_message_id, vote_yes=True)
        # count vote No
        elif data == 'msg_check_vote_scam_no':
            db.update_scam_voting(chat_id, scam_message_id, vote_yes=False)
    except Exception as e:
        logging.error(f"Error during dispatch of group message voting: {e}")
        await query.answer("Failed to process your vote.")

# antiflood checker
async def antiflood_checker(update, context, interval=10):
    try:
        user_id = update.effective_user.id
        group_id = update.effective_chat.id
        now = datetime.now()

        # initialize a placeholder in context for flood control, if doesn't exist
        if 'flood_control' not in context.bot_data:
            context.bot_data['flood_control'] = {}
        user_key = f"{group_id}_{user_id}"

        # add current message timestamp + update_id
        if user_key not in context.bot_data['flood_control']:
            context.bot_data['flood_control'][user_key] = [(now, update.update_id)]
        else:
            context.bot_data['flood_control'][user_key].append((now, update.update_id))
            context.bot_data['flood_control'][user_key] = [
                (timestamp, update_id) for timestamp, update_id in context.bot_data['flood_control'][user_key] 
                if now - timestamp < timedelta(seconds=20)
            ]

            if len(context.bot_data['flood_control'][user_key]) > interval:
                mute_duration = timedelta(minutes=5)
                until_time = now + mute_duration
                await context.bot.restrict_chat_member(group_id, user_id, permissions=ChatPermissions(can_send_messages=False), until_date=until_time.timestamp())
                antiflood_warning_message = f"⛔ Stop flooding! ⛔\n\nTo prevent spamming chats with unnecessary information, group admins have set a limit of max. <b>{interval} messages every 20 seconds</b>!"
                message = await context.bot.send_message(group_id, antiflood_warning_message, parse_mode=ParseMode.HTML)
                await utils.delete_message_after(context, group_id, message.message_id, delay_seconds=30)
                context.bot_data['flood_control'][user_key] = []
    except Exception as e:
        logging.error(f"Error in antiflood_checker: {e}")
        await context.bot.send_message(group_id, "Failed to enforce anti-flood measures.")
