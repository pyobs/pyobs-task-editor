import abc
import pydantic
from urllib.parse import urljoin
import requests
from pyobs.robotic import Task


class User(pydantic.BaseModel):
    id: int = pydantic.Field(default=None)
    username: str = pydantic.Field(default="")
    email: str = pydantic.Field(default="")
    is_superuser: bool = pydantic.Field(default=False)


class Project(pydantic.BaseModel):
    id: int = pydantic.Field(default=0)
    code: str
    name: str
    priority: float
    users: list[str] = pydantic.Field(default=[])


class Backend(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get_users(self): ...

    @abc.abstractmethod
    def add_user(self, user: User): ...

    @abc.abstractmethod
    def update_user(self, user: User): ...

    @abc.abstractmethod
    def get_projects(self): ...

    @abc.abstractmethod
    def add_project(self, project: Project): ...

    @abc.abstractmethod
    def update_project(self, project: Project): ...

    @abc.abstractmethod
    def get_tasks(self, project: Project | None = None): ...

    @abc.abstractmethod
    def add_task(self, task: Task): ...

    @abc.abstractmethod
    def update_task(self, task: Task): ...


class HttpBackend(Backend):
    def __init__(self, url: str = "http://localhost:8008/"):
        self._url = url
        self._headers = {"Authorization": "Token d4e46d724a6e33da2c8d64d8d5230988bb0b9682"}  # local debug token

    def get_users(self):
        req = requests.get(urljoin(self._url, "/api/users/"), headers=self._headers)
        return [User.model_validate(user) for user in req.json()]

    def add_user(self, user: User):
        requests.post(urljoin(self._url, "/api/users/"), json=user.model_dump(mode="json"), headers=self._headers)

    def update_user(self, user: User):
        req = requests.put(
            urljoin(self._url, f"/api/users/{user.id}/"),
            json=user.model_dump(mode="json"),
            headers=self._headers,
        )

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

    def get_tasks(self, project: Project | None = None):
        if project is None:
            req = requests.get(urljoin(self._url, "/api/tasks/"), headers=self._headers)
        else:
            req = requests.get(urljoin(self._url, f"/api/projects/{project.id}/tasks/"), headers=self._headers)
        return [Task.model_validate(task) for task in req.json()]

    def add_task(self, task: Task):
        requests.post(urljoin(self._url, "/api/tasks/"), json=task.model_dump(mode="json"), headers=self._headers)

    def update_task(self, task: Task):
        requests.put(
            urljoin(self._url, f"/api/tasks/{task.id}/"), json=task.model_dump(mode="json"), headers=self._headers
        )
