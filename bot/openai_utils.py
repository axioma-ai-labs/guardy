from dotenv import load_dotenv
from openai import AsyncOpenAI
import asyncio
import logging
import bot.resource_utils as utils
import bot.config as config
from telegram.constants import ParseMode

# configuration
load_dotenv()
CONFIG = config.get_config()

# enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# assistants api class
class SupportAssistant:

    def __init__(self, assistant_id, api_key):
        self.client = AsyncOpenAI(api_key=api_key)
        self.assistant_id = assistant_id

    async def create_thread_and_run(self, user_message: str):
        try:
            thread = await self.client.beta.threads.create()
            run = await self.submit_message(thread, user_message)
            return thread, run
        except Exception as e:
            logger.error(f"Error creating thread or submitting message: {e}")
            raise

    async def submit_message(self, thread, user_message: str):
        try:
            await self.client.beta.threads.messages.create(
                thread_id=thread.id, role="user", content=user_message
            )
            return await self.client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=self.assistant_id,
            )
        except Exception as e:
            logger.error(f"Error submitting message or creating run: {e}")
            raise

    async def get_response(self, thread):
        try:
            messages = await self.client.beta.threads.messages.list(thread_id=thread.id)
            assistant_answer = messages.data[0].content[0].text.value
            return assistant_answer
        except Exception as e:
            logger.error(f"Error retrieving assistant response: {e}")
            raise

    async def wait_on_run(self, run, thread):
        try:
            while run.status == "queued" or run.status == "in_progress":
                run = await self.client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
                logger.debug('Responding...')
                await asyncio.sleep(0.5)
            return run
        except Exception as e:
            logger.error(f"Error during run waiting: {e}")
            raise

# activate premium in guardy community
async def activate_premium_assistance(update, context, chat_id:int, OPENAI_GUARDY_ASSISTANT_ID:str, OPENAI_GUARDY_ASSISTANT_API_KEY:str):
    message = update.message.text

    PREMIUM_GROUPS = config.premium_groups['premium_groups_id']

    # check if in premium groups
    if chat_id in PREMIUM_GROUPS and message.startswith(CONFIG.GUARDY_USERNAME):

        # todo: add user validation check whether user exceed 5 oai messages/month. automatic renewal for all users on 01. of each month!
        
        # config oai assistant
        placeholders = config.config_data['placeholders']
        assistant = SupportAssistant(assistant_id=OPENAI_GUARDY_ASSISTANT_ID, api_key=OPENAI_GUARDY_ASSISTANT_API_KEY)

        # remove bot mention
        message = message.replace("@" + context.bot.username, "").strip()

        # check if message is empty or none
        if not message:
            empty_message = await context.bot.send_message(chat_id=chat_id, text="You sent an <b>empty message</b>. Please ask me something!", parse_mode=ParseMode.HTML)
            await utils.delete_message_after(context, chat_id, empty_message.message_id, delay_seconds=10)
            return

        try:
            # placeholder init
            placeholder_message = await update.message.reply_text("🔍 Looking in my mind palace...")
            await update.message.chat.send_action(action="typing")
            await asyncio.sleep(3)

            try:                
                # openai call
                thread, run = await assistant.create_thread_and_run(message)
                run = await assistant.wait_on_run(run, thread)
                answer = await assistant.get_response(thread)
                cleaned_answer = utils.remove_sources_from_response(answer)

                # send successful answer
                await context.bot.edit_message_text(cleaned_answer, chat_id=placeholder_message.chat_id, message_id=placeholder_message.message_id, parse_mode=ParseMode.HTML)

            except Exception as e:
                error_text = f"Something went wrong during completion. Reason: {e}"
                logger.error(error_text)
                await context.bot.edit_message_text('Something went wrong. Try once again...', chat_id=placeholder_message.chat_id, message_id=placeholder_message.message_id)

        except Exception as e:
            error_text = f"Error during handling response: {e}"
            logger.error(error_text)
            error_message = await update.message.reply_text('Something went wrong. Try once again...')
            await utils.delete_message_after(context, chat_id, message_id=error_message.message_id)
        
    else:
        return
