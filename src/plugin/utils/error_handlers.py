from time import sleep
import googleapiclient.discovery
import logging

_LOGGER = logging.getLogger("spaceone")


def api_retry_handler(default_response=None):
    def decorator(method):
        def wrapper(self, *args, **kwargs):
            trial = 0
            while trial < 10:
                try:
                    return method(self, *args, **kwargs)
                except Exception as e:
                    _LOGGER.debug(
                        f"{self.__repr__()} Retrying {method.__name__}({args}, {kwargs}, trial={trial + 1}): {str(e)}"
                    )
                    sleep(1 + 0.002**trial)
                    self.client = googleapiclient.discovery.build(
                        self.google_client_service,
                        self.version,
                        credentials=self.credentials,
                    )
                    trial += 1
            _LOGGER.error(
                f"{self.__repr__()} Failed to {method.__name__}({args}, {kwargs})"
            )
            return default_response

        return wrapper

    return decorator
