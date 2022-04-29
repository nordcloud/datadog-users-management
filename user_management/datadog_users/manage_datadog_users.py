from datadog_api_client.v2 import ApiClient, Configuration
from datadog_api_client.v2.api.roles_api import RolesApi
from datadog_api_client.v2.api.users_api import UsersApi
from datadog_api_client.v2.model.relationship_to_user import RelationshipToUser
from datadog_api_client.v2.model.relationship_to_user_data import RelationshipToUserData
from datadog_api_client.v2.model.users_type import UsersType
from .admin_users import ADMIN_USERS
from functools import cached_property


class ManageDatadogUsers:
    def __init__(self, api_key, app_key, datadog_url):
        self.config = Configuration(
            api_key={"apiKeyAuth": api_key, "appKeyAuth": app_key},
            server_variables={"site": datadog_url},
        )
        self.api_client = ApiClient(self.config)
        self.user_list = {}

    @cached_property
    def organization_roles(self):
        user_roles = {}
        api_instance = RolesApi(self.api_client)
        raw_roles = api_instance.list_roles()

        for role in raw_roles.data:
            user_roles[role["id"]] = role["attributes"].name

        return user_roles

    def get_organization_users(self):
        api_instance = UsersApi(self.api_client)
        users = api_instance.list_users(page_size=1000)

        for user in users.data:
            user_email = user["attributes"].email
            user_status = user["attributes"].status
            user_role_id = user["relationships"].roles.data[0].id

            if user_role_id in self.organization_roles.keys():
                user_role_name = self.organization_roles[user_role_id]
            else:
                user_role_name = self.get_role_name_by_id(user_role_id)

            if "@nordcloud.com" in user_email:
                is_nordcloud_user = True
            else:
                is_nordcloud_user = False

            if user_status != "Disabled":
                self.user_list[user_email] = {
                    "id": user.id,
                    "email": user_email,
                    "status": user_status,
                    "role": user_role_name,
                    "nordcloud_user": is_nordcloud_user,
                    "to_disable": False,
                }

            if user_status == "Pending":
                self.user_list[user_email].update({"to_disable": True})

        return self.user_list

    def get_role_name_by_id(self, role_id):
        api_instance = RolesApi(self.api_client)
        role_response = api_instance.get_role(role_id=role_id)
        role_data = role_response.data
        self.organization_roles[role_id] = role_data["attributes"].name

        return role_data["attributes"].name

    def disable_multiple_users(self, user_list):
        disabled_users = []
        for user in user_list.values():
            if user["to_disable"]:
                self.disable_user_account(user["id"])
                disabled_users.append(user)

        return disabled_users

    def get_role_id(self, role_name):
        for role_id, name in self.organization_roles.items():
            if name == role_name:
                return role_id

    def downgrade_external_user_to_read_only(self, user_list):
        downgraded_users = []
        for user in user_list.values():
            if (
                not "@nordcloud.com" in user["email"]
                and not user["to_disable"]
                and user["role"] != "Datadog Read Only Role"
            ):
                self.add_user_to_role(
                    user["id"], self.get_role_id("Datadog Read Only Role")
                )
                self.remove_user_from_role(
                    user["id"], self.get_role_id("Datadog Admin Role")
                )
                self.remove_user_from_role(
                    user["id"], self.get_role_id("Datadog Standard Role")
                )
                user["role"] = "Datadog Read Only Role"

                downgraded_users.append(user)

        return downgraded_users

    def downgrade_internal_admins_to_standard_role(self, user_list):
        downgraded_users = []
        for user in user_list.values():
            if (
                "@nordcloud.com" in user["email"]
                and user["role"] == "Datadog Admin Role"
                and not user["email"] in ADMIN_USERS
                and not user["to_disable"]
            ):
                self.add_user_to_role(
                    user["id"], self.get_role_id("Datadog Standard Role")
                )
                self.remove_user_from_role(
                    user["id"], self.get_role_id("Datadog Admin Role")
                )
                user["role"] = "Datadog Standard Role"

                downgraded_users.append(user)

        return downgraded_users

    def disable_user_account(self, user_id):
        api_instance = UsersApi(self.api_client)
        try:
            api_instance.disable_user(user_id=user_id)
        except:
            print(f"Failed to disable user {user_id}")

    def add_user_to_role(self, user_id, role_id):
        body = RelationshipToUser(
            data=RelationshipToUserData(id=user_id, type=UsersType("users"))
        )

        api_instance = RolesApi(self.api_client)
        api_instance.add_user_to_role(role_id=role_id, body=body)

    def remove_user_from_role(self, user_id, role_id):
        body = RelationshipToUser(
            data=RelationshipToUserData(id=user_id, type=UsersType("users"))
        )

        api_instance = RolesApi(self.api_client)
        api_instance.remove_user_from_role(role_id=role_id, body=body)
