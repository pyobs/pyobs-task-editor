import abc

import pydantic
from urllib.parse import urljoin
import requests
from pyobs.robotic import Task


class Project(pydantic.BaseModel):
    id: int = pydantic.Field(default=0)
    code: str = pydantic.Field(default="")
    name: str = pydantic.Field(default="")
    priority: float = pydantic.Field(default=0)


class Backend(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get_projects(self): ...

    @abc.abstractmethod
    def add_project(self, project: Project): ...

    @abc.abstractmethod
    def update_project(self, project: Project): ...

    @abc.abstractmethod
    def get_tasks(self): ...

    @abc.abstractmethod
    def add_task(self, task: Task): ...

    @abc.abstractmethod
    def update_task(self, task: Task): ...


class HttpBackend(Backend):
    def __init__(self, url: str = "http://localhost:8008/"):
        self._url = url
        self._headers = {"Authorization": "Token 484737b0e9001bdfabb7e96d68c98cd91e4d4d24"}  # local debug token

    def get_projects(self):
        req = requests.get(urljoin(self._url, "/api/projects/"), headers=self._headers)
        return [Project.model_validate(project) for project in req.json()]

    def add_project(self, project: Project):
        requests.post(urljoin(self._url, "/api/projects/"), json=project.model_dump(mode="json"), headers=self._headers)

    def update_project(self, project: Project):
        requests.put(
            urljoin(self._url, f"/api/projects/{project.id}/"),
            json=project.model_dump(mode="json"),
            headers=self._headers,
        )

    def get_tasks(self):
        req = requests.get(urljoin(self._url, "/api/tasks/"), headers=self._headers)
        return [Task.model_validate(task) for task in req.json()]

    def add_task(self, task: Task):
        print(task.model_dump(mode="json"))
        requests.post(urljoin(self._url, "/api/tasks/"), json=task.model_dump(mode="json"), headers=self._headers)

    def update_task(self, task: Task):
        requests.put(
            urljoin(self._url, f"/api/tasks/{task.id}/"), json=task.model_dump(mode="json"), headers=self._headers
        )
