import json
from typing import Any, Mapping, Optional

from starlette.background import BackgroundTask
from starlette.responses import Response

from tatami._utils import serialize_json


class JSONResponse(Response):
    def __init__(self, content: Any, status_code: int = 200, headers: Optional[Mapping[str, str]] = None, media_type: Optional[str] = None, background: Optional[BackgroundTask] = None):
        headers = headers or {}
        headers['content-type'] = 'application/json'
        serialized = serialize_json(content)
        json_encoded = json.dumps(serialized)
        super().__init__(json_encoded, status_code, headers, media_type, background)
