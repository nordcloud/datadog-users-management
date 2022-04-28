# Copyright 2021 Nordcloud Oy or its affiliates. All Rights Reserved.
import logging
from .user import User
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


class SlackConnect:
    def __init__(self, token):
        self.slack_client = WebClient(token=token)
        self.logger = logging.getLogger(__name__)

    def get_users(self):
        try:
            users_list = []
            result = self.slack_client.users_list()

            while result:
                for user in result["members"]:
                    if user["deleted"] and "email" in user["profile"] and '@nordcloud.com' in user["profile"]["email"]:
                        users_list.append(
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

            return users_list

        except SlackApiError as e:
            self.logger.exception("Slack error: {}".format(e))
