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
        return result.get("groups", [])

    def get_group(self, name):
        result = self.client.groups().get(name=name).execute()
        return result

    def list_memberships(self, parent):
        memberships = []
        request = self.client.groups().memberships().list(parent=parent)

        while True:
            response = request.execute()

            memberships.extend(response.get("memberships", []))

            request = (
                self.client.groups().memberships()
                .list_next(previous_request=request, previous_response=response)
            )

            if request is None:
                break

        return memberships

    def get_membership(self, name):
        return self.client.groups().memberships().get(name=name).execute()
