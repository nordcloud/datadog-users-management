import logging
from .user import User
from slack_sdk import WebClient
import os


class SlackConnect:
    def __init__(self):
        self.token = os.environ["SLACK_API_KEY"]
        self.slack_client = WebClient(token=self.token)
        self.logger = logging.getLogger(__name__)

    def get_users(self):
        disabled_user_list = []
        result = self.slack_client.users_list()

        while result:
            for user in result["members"]:
                if user["deleted"] and "@nordcloud.com" in user["profile"].get(
                    "email", ""
                ):
                    disabled_user_list.append(
                        User(
                            id=user["id"],
                            name=user["profile"]["real_name"],
                            email=user["profile"]["email"],
                        )
                    )
            if cursor := result["response_metadata"].get("next_cursor"):
                result = self.slack_client.users_list(cursor=cursor)
            else:
                result = None

        return disabled_user_list
