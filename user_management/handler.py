# Copyright 2021 Nordcloud Oy or its affiliates. All Rights Reserved.
import os
import logging
import json
from slack_users.get_slack_users import SlackConnect
from datadog_users.manage_datadog_users import ManageDatadogUsers
from slack_users.user import User

logger = logging.getLogger(__name__)
SLACK_API_TOKEN = os.environ.get("SLACK_API_KEY")
DD_URLS = {"EU": "datadoghq.eu", "US": "datadoghq.com"}


def export_users_data(user_data):
    with open("datadog_users.json", "w") as output:
        json.dump(user_data, output, sort_keys=True)

    print("Successfully exported to json")


def find_leavers_in_org(all_users: list[dict], slack_leavers: list[User]):
    leavers = []
    for user in slack_leavers:
        for person in all_users:
            if user.email == person["email"]:
                leavers.append(person)

    return leavers


def handler():
    result = {}
    disabled_slack_users = []

    if not SLACK_API_TOKEN:
        logger.error("Failed to obtain Slack token")
    else:
        connect_slack = SlackConnect(SLACK_API_TOKEN)
        disabled_slack_users = connect_slack.get_users()

    keys = json.load(open("test.json"))

    for details in keys.values():
        org_name = details["name"]
        org_location = details["location"]
        disabled_org_users = []
        downgraded_org_users = []

        print(f"Processing {org_name} - {org_location}")

        api_session = ManageDatadogUsers(
            details["api_key"], details["app_key"], DD_URLS[org_location]
        )

        org_roles = api_session.get_organization_roles()

        (
            all_users,
            users_to_downgrade,
            users_to_disable,
        ) = api_session.get_organization_users(org_roles)

        if users_to_downgrade:
            downgraded_org_users = api_session.downgrade_external_user_to_read_only(
                users_to_downgrade
            )

            downgraded_internal_users = (
                api_session.downgrade_internal_admins_to_standard_role(
                    users_to_downgrade
                )
            )
            for user in downgraded_internal_users:
                if user not in downgraded_org_users:
                    downgraded_org_users.append(user)

        leavers_list = find_leavers_in_org(all_users, disabled_slack_users)
        if leavers_list:
            for user in leavers_list:
                if user not in users_to_disable:
                    users_to_disable.append(user)

        if users_to_disable:
            disabled_org_users = api_session.disable_multiple_users(users_to_disable)

        result[org_name] = {
            "users": all_users,
            "location": DD_URLS[org_location],
            "downgraded_users": downgraded_org_users,
            "disabled_users": disabled_org_users,
        }
        export_users_data(result)
        print(
            f"Organization {org_name} processed. Disabled {len(disabled_org_users)} users. Downgraded {len(downgraded_org_users)} users."
        )


handler()
