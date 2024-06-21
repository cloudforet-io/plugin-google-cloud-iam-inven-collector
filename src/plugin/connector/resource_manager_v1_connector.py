import logging

from plugin.connector import GoogleCloudConnector

__all__ = ["ResourceManagerV1Connector"]

_LOGGER = logging.getLogger("spaceone")


class ResourceManagerV1Connector(GoogleCloudConnector):
    google_client_service = "cloudresourcemanager"
    version = "v1"

    def list_projects(self):
        result = self.client.projects().list().execute()
        return result.get("projects", [])
