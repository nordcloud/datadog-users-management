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


def mark_leavers_to_disable(all_users: dict[dict], slack_leavers: list[User]):
    leaver_emails = {user.email for user in slack_leavers}
    for person in all_users.values():
        if person["email"] in leaver_emails:
            person["to_disable"] = True


def handler():
    result = {}
    disabled_slack_users = []

    if not SLACK_API_TOKEN:
        logger.error("Failed to obtain Slack token")
    else:
        connect_slack = SlackConnect()
        disabled_slack_users = connect_slack.get_users()

    with open("test.json") as file:
        keys = json.load(file)

        for details in keys.values():
            org_name = details["name"]
            org_location = details["location"]

            print(f"Processing {org_name} - {org_location}")

            dd = ManageDatadogUsers(
                details["api_key"], details["app_key"], DD_URLS[org_location]
            )

            all_users = dd.get_organization_users()

            downgraded_org_users = dd.downgrade_external_user_to_read_only(all_users)
            downgraded_internal_users = dd.downgrade_internal_admins_to_standard_role(
                all_users
            )

            for user in downgraded_internal_users:
                if user not in downgraded_org_users:
                    downgraded_org_users.append(user)

            mark_leavers_to_disable(all_users, disabled_slack_users)
            disabled_org_users = dd.disable_multiple_users(all_users)

            result[org_name] = {
                "users": all_users,
                "location": DD_URLS[org_location],
                "downgraded_users": downgraded_org_users,
                "disabled_users": disabled_org_users,
            }

            print(
                f"Organization {org_name} processed. Disabled {len(disabled_org_users)} users. Downgraded {len(downgraded_org_users)} users."
            )

        export_users_data(result)


handler()
