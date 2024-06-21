import logging
from plugin.connector import GoogleCloudConnector

__all__ = ["CloudIdentityConnector"]

_LOGGER = logging.getLogger("spaceone")


class CloudIdentityConnector(GoogleCloudConnector):
    google_client_service = "cloudidentity"
    version = "v1"

    def list_groups(self, customer_id):
        parent = f"customers/{customer_id}"
        result = self.client.groups().list(parent=parent).execute()
        print(result)
        return result.get("groups", [])

    def list_memberships(self, parent):
        result = self.client.groups().memberships(parent=parent).list().execute()
        return result.get("memberships", [])
