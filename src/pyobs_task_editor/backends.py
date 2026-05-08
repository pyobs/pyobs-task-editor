from urllib.parse import urljoin
import requests
from pyobs.robotic import Task


class HttpBackend:
    def __init__(self, url: str = "http://localhost:8008/"):
        self._url = url

    def get_tasks(self):
        req = requests.get(urljoin(self._url, "/api/tasks/"))
        return [Task.model_validate(task) for task in req.json()]

    def add_task(self, task: Task):
        print(task.model_dump(mode="json"))
        requests.post(urljoin(self._url, "/api/tasks/"), json=task.model_dump(mode="json"))

    def update_task(self, task: Task):
        requests.put(urljoin(self._url, f"/api/tasks/{task.id}/"), json=task.model_dump(mode="json"))
