import logging
from plugin.connector import GoogleCloudConnector
import requests
import google.auth.transport.requests
from plugin.utils.error_handlers import api_retry_handler

__all__ = ["LoggingConnector"]

_LOGGER = logging.getLogger("spaceone")


class LoggingConnector(GoogleCloudConnector):
    google_client_service = "logging"
    version = "v2"

    @api_retry_handler(default_response=[])
    def list_entries(self, project_id: str) -> list:
        body = {
            "resourceNames": [f"projects/{project_id}"],
            "orderBy": "timestamp desc",
            "pageSize": 10,
        }
        response = self.client.entries().list(body=body).execute()

        entries = response.get("entries", [])
        return entries

    def get_all_service_account_last_authenticated_time(self, project_id: str):
        return self._get_all_service_account_last_authenticated_time(project_id, is_key=False)

    def get_all_service_account_key_last_authenticated_time(self, project_id: str):
        return self._get_all_service_account_last_authenticated_time(project_id, is_key=True)

    @api_retry_handler(default_response={})
    def _get_all_service_account_last_authenticated_time(self, project_id: str, is_key: bool):
        activity_type = "serviceAccountLastAuthentication" if not is_key else "serviceAccountKeyLastAuthentication"
        page_size = 1000
        url = f"https://policyanalyzer.googleapis.com/v1/projects/{project_id}/locations/global/activityTypes/{activity_type}/activities:query?pageSize={page_size}"
        scopes = ["https://www.googleapis.com/auth/cloud-platform"]
        credentials = self.credentials.with_scopes(scopes)
        request = google.auth.transport.requests.Request()
        credentials.refresh(request)
        token = credentials.token
        headers = {
            "Authorization": f"Bearer {token}"
        }
        sa_id_to_last_authenticated_time = {}
        next_page_token = ""
        while True:
            response = requests.get(url+next_page_token, headers=headers)
            if response.status_code != 200:
                error_message = f"API request failed with status code {response.status_code}: {response.text}"
                _LOGGER.debug(f"[{self.__repr__()}] Error: {error_message}", exc_info=True)
                if response.status_code == 403:
                    return None
                return sa_id_to_last_authenticated_time
            activities = response.json().get('activities', [])
            if not activities:
                break
            for one_sa_dict in activities:

                sa_id = one_sa_dict.get('activity', {}).get('serviceAccount', {}).get('serviceAccountId', '')
                sa_id = sa_id if sa_id else one_sa_dict.get('activity', {}).get('serviceAccountKey', {}).get('serviceAccountId', '')

                last_authenticated_time = one_sa_dict.get('activity', {}).get('lastAuthenticatedTime', '')

                if is_key:

                    key_id = one_sa_dict.get('fullResourceName', '').split("/")[-1]

                    if sa_id not in sa_id_to_last_authenticated_time:
                        sa_id_to_last_authenticated_time[sa_id] = {}
                    sa_id_to_last_authenticated_time[sa_id][key_id] = last_authenticated_time
                else:
                    sa_id_to_last_authenticated_time[sa_id] = last_authenticated_time

            next_page_token = response.json().get('nextPageToken')
            if not next_page_token:
                break
            url += "&pageToken="
        return sa_id_to_last_authenticated_time
