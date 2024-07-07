import logging
from plugin.connector import GoogleCloudConnector

__all__ = ["LoggingConnector"]

_LOGGER = logging.getLogger("spaceone")


class LoggingConnector(GoogleCloudConnector):
    google_client_service = "logging"
    version = "v2"

    def list_entries(self, project_id: str) -> list:
        body = {
            "resourceNames": [f"projects/{project_id}"],
            "orderBy": "timestamp desc",
            "pageSize": 10,
        }
        response = self.client.entries().list(body=body).execute()

        entries = response.get("entries", [])
        return entries
