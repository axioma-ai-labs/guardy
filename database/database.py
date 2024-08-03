from pymongo import MongoClient
from typing import Dict
from datetime import datetime
import logging

class MongoDBManager:
    # collections
    PRIVATE_CHATS = "PrivateChats"
    GROUP_CHATS = "GroupChats"
    GROUP_CHAT_CONFIGS = "GroupChatConfigs"
    GROUP_CHAT_VERIFICATIONS = "GroupChatVerifications"
    GROUP_CHAT_SCAM_VOTING = "GroupChatScamVoting"

    def __init__(self, uri):
        """
        initialize the MongoDBManager with a uri and database name.

        parameters:
        - uri (str): mongodb uri connection string.
        - db_name (str): the name of the database to connect to.

        usage:
        db_manager = MongoDBManager("mongodb://localhost:27017/", "mydatabase")
        """
        self.client = MongoClient(uri)
        self.db = self.client["ChatDB"]
        self.collections = self.db.list_collection_names()
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    # add new group (public group): works
    def add_new_public_group(self, group_id:int, added_by:int, member_count:int, chat_title:str="", chat_username:str="", chat_type:str=""):
        """
        add a new public group to the database.

        parameters:
        - group_id (int): id of the chat.
        - chat_title (str): title of the chat.
        - chat_username (str): username of the chat.
        - chat_type (str): type of the chat (e.g., 'group', 'supergroup').
        - added_by (int): user id of the person who added bot to the group.

        usage:
        db_manager.add_new_public_group(12345, 321214, 250, "My Group", "mygroup", "supergroup", 98765)
        """
        try:
            group_data = {
                "date_added": datetime.now(),
                "group_id": group_id,
                "member_count": member_count,
                "chat_title": chat_title,
                "chat_username": chat_username,
                "chat_type": chat_type,
                "added_by": added_by
            }
            self.db[self.GROUP_CHATS].insert_one(group_data)
        except Exception as e:
            self.logger.error(f"Failed to add new public group: {e}")

    # add new user (private chat): works
    def add_new_private_user(self, user_id:int, username:str="", first_name:str="", last_name:str=""):
        """
        adds a new private chat user to the database. 
        it first checks if the user already exists in the collection and adds only if the user is not present.

        args:
            user_id (int): the id of the user.
            chat_id (int): the chat id associated with the user.
            username (str, optional): the username of the user. defaults to an empty string.
            first_name (str, optional): the first name of the user. defaults to an empty string.
            last_name (str, optional): the last name of the user. defaults to an empty string.

        usage:
            db_manager.add_new_private_user(123456, "username", "First", "Last")
        """
        try:
            if not self.check_if_user_exists(user_id):
                user_dict = {
                    "date_added": datetime.now(),
                    "user_id": user_id,
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                }
                self.db[self.PRIVATE_CHATS].insert_one(user_dict)
        except Exception as e:
            self.logger.error(f"Failed to add new private user: {e}")

    # delete user by id: works
    def delete_private_user_by_id(self, user_id:int):
        """
        deletes a user from the specified collection based on their user id.

        parameters:
        - user_id (int): the user id of the user to delete.

        usage:
        db_manager.delete_private_user_by_id(123456)
        """
        try:
            if self.check_if_user_exists(user_id):
                self.db[self.PRIVATE_CHATS].delete_one({"user_id": user_id})
        except Exception as e:
            self.logger.error(f"Failed to delete private user by ID: {e}")

    # check if user exists: works
    def check_if_user_exists(self, user_id:int):
        """
        check if a user exists in the specified collection.

        parameters:
        - user_id (int): the id of the user to check for.

        returns:
        - bool: true if the user exists, false otherwise.

        usage:
        user_exists = db_manager.check_if_user_exists(123456)
        """
        try:
            user_doc = self.db[self.PRIVATE_CHATS].find_one({"user_id": user_id})
            return user_doc is not None
        except Exception as e:
            self.logger.error(f"Failed to check if user exists: {e}")
            return False

    # check if group exists: works
    def check_if_group_exists(self, group_id:int):
        """
        check if a group exists in the specified collection.

        parameters:
        - group_id (int): the id of the group to check for.

        returns:
        - bool: true if the group exists, false otherwise.

        usage:
        group_exists = db_manager.check_if_group_exists(123456)
        """
        try:
            group_doc = self.db[self.GROUP_CHATS].find_one({"group_id": group_id})
            return group_doc is not None
        except Exception as e:
            self.logger.error(f"Failed to check if group exists: {e}")
            return False

    # check if group admin config exists: works
    def check_if_admin_config_exists(self, group_id:int):
        """
        checks if the admin configuration for a given group exists in the database.

        args:
            group_id (int): the id of the group to check for.

        returns:
            bool: true if the admin configuration exists, false otherwise.

        usage:
            config_exists = db_manager.check_if_admin_config_exists(123456)
        """
        try:
            group_doc = self.db[self.GROUP_CHAT_CONFIGS].find_one({"group_id": group_id})
            return group_doc is not None
        except Exception as e:
            self.logger.error(f"Failed to check if admin config exists: {e}")
            return False

    # set group admin configuration: works
    def set_admin_config(self, group_id: int, config_data: Dict):
        """
        set or update the admin configuration for a specific group.

        parameters:
        - group_id (int): the id of the group.
        - config_data (Dict): the configuration data to set or update.

        usage:
        db_manager.set_admin_configuration(123456789, {"link_removal": "Yes", "forwarded_removal": "No", ...})
        """
        try:
            current_time = datetime.now()
            updated_data = {
                "$set": config_data,
                "$setOnInsert": {"group_id": group_id, "created_at": current_time},
                "$currentDate": {"last_updated": True}
            }
            self.db[self.GROUP_CHAT_CONFIGS].update_one({"group_id": group_id}, updated_data, upsert=True)
        except Exception as e:
            self.logger.error(f"Failed to set admin configuration: {e}")

    # show group admin configuration: works
    def get_admin_config(self, group_id: int):
        """
        fetches the admin configuration for a given group.

        parameters:
        - group_id (int): the group id.

        returns:
        a dictionary containing the group's configuration or none if not found.
        """
        try:
            config_data = self.db[self.GROUP_CHAT_CONFIGS].find_one({"group_id": group_id})
            return config_data  # This will be None if not found
        except Exception as e:
            self.logger.error(f"Failed to get admin configuration: {e}")
            return None

    # delete admin config: works
    def delete_admin_config(self, group_id: int):
        """
        deletes the admin configuration for a specific group from the database.

        this function should be used when the admin configuration for a group is no longer needed or relevant.

        args:
            group_id (int): the id of the group whose admin configuration is to be deleted.

        usage:
            db_manager.delete_admin_config(123456789)
        """
        try:
            if self.check_if_admin_config_exists(group_id):
                self.db[self.GROUP_CHAT_CONFIGS].delete_one({"group_id": group_id})
        except Exception as e:
            self.logger.error(f"Failed to delete admin configuration: {e}")

    # store user verification data: works
    def store_verification_data(self, group_id: int, group_username:str, group_title:str, welcome_message_id:int, user_id:int, verification_type:str, verified:bool):
        """
        store verification data for a group chat in the database.

        parameters:
        - group_id (int): id of the group.
        - group_username (str): username of the group.
        - group_title (str): title of the group.
        - welcome_message_id (int): id of the welcome message sent in the group.
        - user_id (int): id of the user being verified.
        - verification_type (str): verification type for the group
        - verified (bool): verification status of the user.

        usage:
        db_manager.store_verification_data(123456, "mygroup", "My Group", 654321, 123456, "web", False)
        """
        try:
            verification_data = {
                "date_added": datetime.now(),
                "group_id": group_id,
                "group_username": group_username,
                "group_title": group_title,
                "welcome_message_id": welcome_message_id,
                "user_id": user_id,
                "verification_type": verification_type,
                "verified": verified
            }

            self.db[self.GROUP_CHAT_VERIFICATIONS].insert_one(verification_data)
        except Exception as e:
            self.logger.error(f"Failed to store verification data: {e}")

    # delete verification data based on the user_id & verification status
    def delete_verification_data(self, user_id:int):
        """
        deletes verification data from the GroupChatVerifications collection for a specific user based on their user id.

        parameters:
        - user_id (int): the id of the user whose verification data is to be deleted.

        usage:
        db_manager.delete_verification_data(123456)
        """
        try:
            if self.check_if_verification_data_exists(user_id):
                self.db[self.GROUP_CHAT_VERIFICATIONS].delete_one({"user_id": user_id})
        except Exception as e:
            self.logger.error(f"Failed to delete verification data: {e}")

    # fetch verification data
    def get_verification_data(self, user_id: int, group_id: int):
        """
        fetches the verification data for a given user and group.

        parameters:
        - user_id (int): the user id.
        - group_id (int): the group id.

        returns:
        a dictionary containing the verification data or none if not found.
        """
        try:
            verification_data = self.db[self.GROUP_CHAT_VERIFICATIONS].find_one({
                "user_id": user_id,
                "group_id": group_id
            })
            return verification_data  # This will be None if not found
        except Exception as e:
            self.logger.error(f"Failed to fetch verification data: {e}")
            return None

    # delete group data
    def delete_group_data(self, group_id: int):
        """
        deletes all data associated with a specific group from the database.

        this function removes the group's record from the GROUP_CHATS collection. it should be used when a group is no longer active or relevant to the database.

        parameters:
        - group_id (int): the id of the group to be deleted.

        usage:
        db_manager.delete_group_data(123456789)
        """
        try:
            if self.check_if_group_exists(group_id):
                self.db[self.GROUP_CHATS].delete_one({"group_id": group_id})
        except Exception as e:
            self.logger.error(f"Failed to delete group data: {e}")

    # add voter to set
    def add_voter(self, group_id: int, scam_message_id: int, user_id: int):
        """
        add a user to the list of voters for a specific scam message in a group.

        parameters:
        - group_id (int): the id of the group.
        - scam_message_id (int): the id of the scam message.
        - user_id (int): the id of the user who voted.

        usage:
        db_manager.add_voter(123456789, 987654321, 111222333)
        """
        try:
            self.db[self.GROUP_CHAT_SCAM_VOTING].update_one(
                {"group_id": group_id, "scam_message_id": scam_message_id},
                {"$addToSet": {"voters": user_id}},
                upsert=True
            )
        except Exception as e:
            self.logger.error(f"Failed to add voter: {e}")

    # check if user has voted or not
    def check_if_user_voted(self, group_id: int, scam_message_id: int, user_id: int) -> bool:
        """
        check if a user has already voted on a specific scam message in a group.

        parameters:
        - group_id (int): the id of the group.
        - scam_message_id (int): the id of the scam message.
        - user_id (int): the id of the user to check.

        returns:
        - bool: true if the user has voted, false otherwise.

        usage:
        has_voted = db_manager.check_if_user_voted(123456789, 987654321, 111222333)
        """
        try:
            voting_record = self.db[self.GROUP_CHAT_SCAM_VOTING].find_one(
                {"group_id": group_id, "scam_message_id": scam_message_id, "voters": user_id}
            )
            return bool(voting_record)
        except Exception as e:
            self.logger.error(f"Failed to check if user has voted: {e}")
            return False

    # upsert scam voting
    def update_scam_voting(self, group_id: int, scam_message_id: int, vote_yes: bool):
        """
        update the scam voting results for a specific message in a group. if the record does not exist, it creates one.
        each call updates either the 'vote_scam_yes' or 'vote_scam_no' count.

        parameters:
        - group_id (int): the id of the group where the voting is taking place.
        - scam_message_id (int): the id of the scam message being voted on.
        - vote_yes (bool): true if the vote is 'Yes' for scam, false for 'No'.

        usage:
        db_manager.update_scam_voting(123456789, 987654321, true)  # for a 'Yes' vote
        db_manager.update_scam_voting(123456789, 987654321, false) # for a 'No' vote
        """
        try:
            update_field = "vote_scam_yes" if vote_yes else "vote_scam_no"
            self.db[self.GROUP_CHAT_SCAM_VOTING].update_one(
                {"group_id": group_id, "scam_message_id": scam_message_id},
                {"$inc": {update_field: 1}},
                upsert=True
            )
        except Exception as e:
            self.logger.error(f"Failed to update scam voting: {e}")

    # init scam voting
    def initialize_scam_voting(self, group_id:int, scam_message_id:int, alert_message_id:int):
        """
        initializes a scam voting record with 'vote_scam_yes' and 'vote_scam_no' set to 0.

        parameters:
        - group_id (int): the id of the group.
        - scam_message_id (int): the id of the scam message.
        - alert_message_id (int): the id of the alert message sent by Guardy

        usage:
        db_manager.initialize_scam_voting(123456789, 987654321)
        """
        try:
            if not self.check_if_scam_voting_item_exists(group_id, scam_message_id):
                self.db[self.GROUP_CHAT_SCAM_VOTING].insert_one({
                    "group_id": group_id,
                    "alert_message_id": alert_message_id,
                    "scam_message_id": scam_message_id,
                    "vote_scam_yes": 0,
                    "vote_scam_no": 0
                })
        except Exception as e:
            self.logger.error(f"Failed to initialize scam voting: {e}")

    # delete scam voting
    def delete_scam_voting(self, group_id: int, scam_message_id: int):
        """
        retrieves and deletes a scam voting record from the GroupChatScamVoting collection.

        parameters:
        - group_id (int): the id of the group.
        - scam_message_id (int): the id of the scam message.

        returns:
        the scam voting record if found, none otherwise.

        usage:
        voting_record = db_manager.delete_scam_voting(123456789, 987654321)
        """
        try:
            # retrieve the record
            query = {"group_id": group_id, "scam_message_id": scam_message_id}
            record = self.db[self.GROUP_CHAT_SCAM_VOTING].find_one_and_delete(query)
            return record
        except Exception as e:
            self.logger.error(f"Failed to delete scam voting: {e}")
            return None
