import logging
from spaceone.core import cache
from plugin.connector import GoogleCloudConnector

__all__ = ["IAMConnector"]

_LOGGER = logging.getLogger("spaceone")


class IAMConnector(GoogleCloudConnector):
    google_client_service = "iam"
    version = "v1"

    def get_service_account(self, name: str):
        return self.client.projects().serviceAccounts().get(name=name).execute()

    def list_service_accounts(self, project_id: str = None) -> list:
        project_id = project_id or self.project_id
        service_accounts = []

        query = {"name": f"projects/{project_id}"}
        request = self.client.projects().serviceAccounts().list(**query)

        while True:
            response = request.execute()
            service_accounts.extend(response.get("accounts", []))
            request = (
                self.client.projects()
                .serviceAccounts()
                .list_next(previous_request=request, previous_response=response)
            )

            if request is None:
                break

        return service_accounts

    def list_service_account_keys(self, service_account_email: str, project_id: str = None):
        project_id = project_id or self.project_id
        query = {
            "name": f"projects/{project_id}/serviceAccounts/{service_account_email}"
        }
        request = self.client.projects().serviceAccounts().keys().list(**query)
        response = request.execute()

        keys = response.get("keys", [])
        return list(filter(lambda x: x.get("keyType") == "USER_MANAGED", keys))

    def query_testable_permissions(self, resource: str):
        body = {"fullResourceName": resource}
        permissions = []

        while True:
            request = self.client.permissions().queryTestablePermissions(body=body)
            response = request.execute()
            permissions.extend(response.get("permissions", []))

            if "nextPageToken" not in response:
                break

            body["pageToken"] = response["nextPageToken"]

        return permissions

    def get_project_role(self, name: str):
        return self.client.projects().roles().get(name=name).execute()

    def list_project_roles(self, project_id: str = None):
        parent = f"projects/{project_id}"
        roles = []
        request = self.client.projects().roles().list(parent=parent)

        while True:
            response = request.execute()

            roles.extend(response.get("roles", []))

            request = (
                self.client.projects()
                .roles()
                .list_next(previous_request=request, previous_response=response)
            )

            if request is None:
                break

        return roles

    def get_organization_role(self, name: str):
        return self.client.organizations().roles().get(name=name).execute()

    def list_organization_roles(self, resource):
        roles = []
        request = self.client.organizations().roles().list(parent=resource)

        while True:
            response = request.execute()
            roles.extend(response.get("roles", []))

            request = (
                self.client.organizations()
                .roles()
                .list_next(previous_request=request, previous_response=response)
            )

            if request is None:
                break

        return roles

    @cache.cacheable(key="plugin:connector:role:{name}", alias="local")
    def get_role(self, name: str):
        return self.client.roles().get(name=name).execute()

    def list_roles(self):
        roles = []
        request = self.client.roles().list(pageSize=1000)

        while True:
            response = request.execute()
            roles.extend(response.get("roles", []))

            request = self.client.roles().list_next(
                previous_request=request, previous_response=response
            )

            if request is None:
                break

        return roles
