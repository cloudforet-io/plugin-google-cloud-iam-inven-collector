import logging
from plugin.connector import GoogleCloudConnector
from plugin.utils.error_handlers import api_retry_handler


__all__ = ["CloudIdentityConnector"]

_LOGGER = logging.getLogger("spaceone")


class CloudIdentityConnector(GoogleCloudConnector):
    google_client_service = "cloudidentity"
    version = "v1"

    @api_retry_handler(default_response=[])
    def list_groups(self, customer_id):
        groups = []
        parent = f"customers/{customer_id}"
        request = self.client.groups().list(parent=parent, pageSize=1000)
        while True:
            response = request.execute()
            groups.extend(response.get("groups", []))
            request = self.client.groups().list_next(
                previous_request=request, previous_response=response
            )
            if request is None:
                break
        return groups

    @api_retry_handler(default_response=[])
    def list_memberships(self, parent):
        memberships = []
        request = (
            self.client.groups()
            .memberships()
            .list(parent=parent, pageSize=500, view="FULL")
        )

        while True:
            response = request.execute()

            memberships.extend(response.get("memberships", []))

            request = (
                self.client.groups()
                .memberships()
                .list_next(previous_request=request, previous_response=response)
            )

            if request is None:
                break

        return memberships
