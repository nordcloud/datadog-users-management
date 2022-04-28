import os
from datadog_api_client.v2 import ApiClient, Configuration
from datadog_api_client.v2.api.roles_api import RolesApi
from datadog_api_client.v2.api.users_api import UsersApi
from datadog_api_client.v2.model.relationship_to_user import RelationshipToUser
from datadog_api_client.v2.model.relationship_to_user_data import RelationshipToUserData
from datadog_api_client.v2.model.users_type import UsersType
from .admin_users import ADMIN_USERS


class ManageDatadogUsers:
    def __init__(self, api_key, app_key, datadog_url):
        os.environ["DD_SITE"] = datadog_url
        os.environ["DD_API_KEY"] = api_key
        os.environ["DD_APP_KEY"] = app_key
        self.api_client = ApiClient(Configuration())
        self.user_roles = {}
        self.user_list = []
        self.users_to_disable = []
        self.users_to_downgrade = []

    def get_organization_users(self, org_user_roles):
        api_instance = UsersApi(self.api_client)
        users = api_instance.list_users(page_size=1000)

        for user in users.data:
            user_email = user["attributes"].email
            user_status = user["attributes"].status
            user_role_id = user["relationships"].roles.data[0].id

            if user_role_id in org_user_roles.values():
                user_role_name = list(org_user_roles.keys())[
                    list(org_user_roles.values()).index(user_role_id)
                ]
            else:
                user_role_name = self.get_role_name_by_id(user_role_id)

            if "@nordcloud.com" in user_email:
                is_nordcloud_user = True
            else:
                is_nordcloud_user = False
                if not user_role_name == "Datadog Read Only Role":
                    self.users_to_downgrade.append(
                        {
                            "email": user_email,
                            "status": user_status,
                            "role": user_role_name,
                            "nordcloud user": is_nordcloud_user,
                            "id": user.id,
                        }
                    )

            if not user_email in ADMIN_USERS and user_role_name == "Datadog Admin Role" and is_nordcloud_user:
                self.users_to_downgrade.append(
                    {
                        "email": user_email,
                        "status": user_status,
                        "role": user_role_name,
                        "nordcloud user": is_nordcloud_user,
                        "id": user.id,
                    }
                )

            if user_status == "Pending":
                self.users_to_disable.append(
                    {
                        "email": user_email,
                        "status": user_status,
                        "role": user_role_name,
                        "nordcloud user": is_nordcloud_user,
                        "id": user.id,
                    }
                )

            if user_status != "Disabled":
                self.user_list.append(
                    {
                        "email": user_email,
                        "status": user_status,
                        "role": user_role_name,
                        "nordcloud user": is_nordcloud_user,
                        "id": user.id,
                    }
                )

        return self.user_list, self.users_to_downgrade, self.users_to_disable

    def get_organization_roles(self):
        api_instance = RolesApi(self.api_client)
        raw_roles = api_instance.list_roles()

        for role in raw_roles.data:
            self.user_roles[role["attributes"].name] = role["id"]

        return self.user_roles

    def get_role_name_by_id(self, role_id):
        api_instance = RolesApi(self.api_client)
        role_response = api_instance.get_role(role_id=role_id)
        role_data = role_response.data
        self.user_roles[role_id] = role_data["attributes"].name

        return role_data["attributes"].name

    def disable_multiple_users(self, user_list):
        disabled_users = []
        for user in user_list:
            self.disable_user_account(user["id"])
            disabled_users.append(user)

        return disabled_users

    def downgrade_external_user_to_read_only(self, user_list):
        downgraded_users = []
        for user in user_list:
            if (
                not "@nordcloud.com" in user["email"]
                and not user["role"] == "Datadog Read Only Role"
            ):
                self.add_user_to_role(
                    user["id"], self.user_roles["Datadog Read Only Role"]
                )
                self.remove_user_from_role(
                    user["id"], self.user_roles["Datadog Admin Role"]
                )
                self.remove_user_from_role(
                    user["id"], self.user_roles["Datadog Standard Role"]
                )
                user["role"] = "Datadog Read Only Role"

            downgraded_users.append(user)

        return downgraded_users

    def downgrade_internal_admins_to_standard_role(self, user_list):
        downgraded_users = []
        for user in user_list:
            if (
                "@nordcloud.com" in user["email"]
                and not user["email"] in ADMIN_USERS
                and user["role"] == "Datadog Admin Role"
            ):
                self.add_user_to_role(
                    user["id"], self.user_roles["Datadog Standard Role"]
                )
                self.remove_user_from_role(
                    user["id"], self.user_roles["Datadog Admin Role"]
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

    def list_role_users(self):
        api_instance = RolesApi(self.api_client)
        for role in self.user_roles.keys():
            print(f"Listing users of {self.user_roles[role]}")
            response = api_instance.list_role_users(role_id=role)
            for user in response.data:
                print(user["attributes"].email)
