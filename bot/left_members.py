import logging
import bot.resource_utils as utils

# enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


# handle removed guardy from the group chat or supergroup
async def handle_left_guardy(update, context, db):

    my_chat_member = update.my_chat_member
    new_status = my_chat_member.new_chat_member.status
    group_id = my_chat_member.chat.id

    # check if the Guardy has been removed from the group
    if new_status == 'left' or new_status == 'kicked':
        logger.info(f"GUARDY has been removed from the group with ID: {group_id}")
        db.delete_group_data(group_id=group_id)
        db.delete_admin_config(group_id=group_id)

    await utils.delete_service_message(update, context)
