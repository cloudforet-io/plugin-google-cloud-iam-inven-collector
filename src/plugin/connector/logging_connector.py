import logging
from plugin.connector import GoogleCloudConnector
from plugin.utils.error_handlers import api_retry_handler

from datetime import datetime, timedelta

__all__ = ["LoggingConnector"]

_LOGGER = logging.getLogger("spaceone")


class LoggingConnector(GoogleCloudConnector):
    google_client_service = "logging"
    version = "v2"

    def __init__(self, options: dict, secret_data: dict, schema: str, *args, **kwargs):
        super().__init__(options=options, secret_data=secret_data, schema=schema, *args, **kwargs)
        self.log_search_period = options.get("log_search_period")

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

    def get_last_log_entry_timestamp(self, project_id: str, service_account_email: str, service_account_key_name: str=None):
        log_entries = (self._list_entries_service_accounts(project_id, service_account_email, service_account_key_name))
        if not log_entries:
            return None
        timestamp = log_entries[0].get("timestamp")
        return timestamp

    @api_retry_handler(default_response=[])
    def _list_entries_service_accounts(self, project_id: str, service_account_email: str, service_account_key_name) -> list:
        filter_str = (
            f"protoPayload.authenticationInfo.principalEmail=\"{service_account_email}\""
        )
        if service_account_key_name:
            full_name = f"//iam.googleapis.com/{service_account_key_name}"
            filter_str += f" AND protoPayload.authenticationInfo.serviceAccountKeyName=\"{full_name}\""
        filter_str += self._get_timestamp_filter_str(datetime.utcnow())

        body = {
            "resourceNames": [f"projects/{project_id}"],
            "orderBy": "timestamp desc",
            "pageSize": 1,
            "filter": filter_str,
        }
        response = self.client.entries().list(body=body).execute()
        entries = response.get("entries", [])
        return entries

    def _get_timestamp_filter_str(self, time_now: datetime) -> str:
        if self.log_search_period == "1 Month":
            log_search_period_in_days = 31
        elif self.log_search_period == "3 Months":
            log_search_period_in_days = 92
        elif self.log_search_period == "6 Months":
            log_search_period_in_days = 183
        else:
            log_search_period_in_days = 365

        start_time, end_time = time_now - timedelta(days=log_search_period_in_days), time_now
        start_time_str, end_time_str = (
            start_time.isoformat().split(".")[0] + "Z",
            end_time.isoformat().split(".")[0] + "Z",
        )
        timestamp_filter = (
            f' AND timestamp >= "{start_time_str}"'
            f' AND timestamp <= "{end_time_str}"'
        )
        return timestamp_filter
