import os
from unittest.mock import MagicMock

import google.auth
import google.cloud.logging

credentials_mock = MagicMock()
google.auth.default = MagicMock(return_value=(credentials_mock, "mock-project"))

os.environ["GOOGLE_CLOUD_PROJECT"] = "mock-project"
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

logging_client_mock = MagicMock()
logger_mock = MagicMock()
logging_client_mock.logger.return_value = logger_mock
google.cloud.logging.Client = MagicMock(return_value=logging_client_mock)
