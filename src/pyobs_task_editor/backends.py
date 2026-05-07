from urllib.parse import urljoin
import requests
from pyobs.robotic import Task


class HttpBackend:
    def __init__(self, url: str = "http://localhost:8008/"):
        self._url = url

    def get_tasks(self):
        req = requests.get(urljoin(self._url, "/api/tasks/"))
        return [Task.model_validate(task) for task in req.json()]
