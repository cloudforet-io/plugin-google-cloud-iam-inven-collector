import logging

__all__ = ["IAMConnector"]

from cloudforet.plugin.connector.base import GoogleCloudConnector

_LOGGER = logging.getLogger("spaceone")


class IAMConnector(GoogleCloudConnector):
    google_client_service = "iam"
    version = "v1"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def list_service_accounts(self, project_id):
        service_accounts = []
        query = {"name": f"projects/{project_id}"}
        request = self.client.projects().serviceAccounts().list(**query)

        while request is not None:
            response = request.execute()
            service_accounts = [
                service_account for service_account in response.get("accounts", [])
            ]
            request = (
                self.client.projects()
                .serviceAccounts()
                .list_next(previous_request=request, previous_response=response)
            )
        return service_accounts

    def list_service_account_keys(self, project_id, service_account_email):
        query = {
            "name": f"projects/{project_id}/serviceAccounts/{service_account_email}"
        }
        request = self.client.projects().serviceAccounts().keys().list(**query)
        response = request.execute()
        return [
            key_info
            for key_info in response.get("keys", [])
            if key_info.get("keyType") == "USER_MANAGED"
        ]

    def list_organization_roles(self, resource):
        roles = []
        request = self.client.organizations().roles().list(parent=resource)

        while request is not None:
            response = request.execute()
            roles.extend(response.get("roles", []))
            request = (
                self.client.organizations()
                .roles()
                .list_next(previous_request=request, previous_response=response)
            )
        return roles

    def list_project_roles(self, project_id):
        parent = f"projects/{project_id}"
        roles = []
        request = self.client.projects().roles().list(parent=parent)

        while request is not None:
            response = request.execute()
            roles.extend(response.get("roles", []))
            request = (
                self.client.projects()
                .roles()
                .list_next(previous_request=request, previous_response=response)
            )
        return roles

    def list_roles(self):
        roles = []
        request = self.client.roles().list(pageSize=1000)

        while request is not None:
            response = request.execute()
            roles.extend(response.get("roles", []))
            request = self.client.roles().list_next(
                previous_request=request, previous_response=response
            )
        return roles
