import abc
import pydantic
from urllib.parse import urljoin
import requests
from astropy.time import Time
from pyobs.robotic import Task
from pyobs.robotic.observation import ObservationList, Observation


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


def _make_json_safe(obj):
    """Recursively convert non-JSON-serializable types to JSON-safe equivalents."""
    if isinstance(obj, Time):
        return obj.isot
    if isinstance(obj, dict):
        return {k: _make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_make_json_safe(v) for v in obj]
    return obj


def _serialize_task(task: Task) -> dict:
    """Serialize a Task, working around Pydantic v2's behaviour of dropping
    subclass fields when serializing polymorphic types as their base class."""
    data = _make_json_safe(task.model_dump())
    data["constraints"] = [_make_json_safe(c.model_dump()) for c in task.constraints]
    data["merits"] = [_make_json_safe(m.model_dump()) for m in task.merits]
    if task.static_target is not None:
        data["target"] = _make_json_safe(task.static_target.model_dump())
    return data


class Backend(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def connect(self) -> User: ...

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

    @abc.abstractmethod
    def get_observations(
        self,
        task: Task | None = None,
        start_before: Time | None = None,
        start_after: Time | None = None,
        end_before: Time | None = None,
        end_after: Time | None = None,
        state: str | None = None,
    ): ...


class HttpBackend(Backend):
    def __init__(self, url: str, token: str) -> None:
        self._url = url
        self._headers = {"Authorization": f"Token {token}"}  # local debug token
        self._user: User | None = None

    def connect(self) -> User:
        req = requests.get(urljoin(self._url, "/api/me/"), headers=self._headers)
        self._user = User.model_validate(req.json())
        return self._user

    def get_users(self):
        req = requests.get(urljoin(self._url, "/api/users/"), headers=self._headers)
        return [User.model_validate(user) for user in req.json()["results"]]

    def add_user(self, user: User):
        requests.post(urljoin(self._url, "/api/users/"), json=user.model_dump(mode="json"), headers=self._headers)

    def update_user(self, user: User):
        requests.put(
            urljoin(self._url, f"/api/users/{user.id}/"),
            json=user.model_dump(mode="json"),
            headers=self._headers,
        )

    def get_projects(self):
        req = requests.get(urljoin(self._url, "/api/projects/"), headers=self._headers)
        return [Project.model_validate(project) for project in req.json()["results"]]

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
            req = requests.get(urljoin(self._url, "/api/tasks/"), headers=self._headers, params={"all": "true"})
        else:
            req = requests.get(urljoin(self._url, f"/api/projects/{project.id}/tasks/"), headers=self._headers)
        return [Task.model_validate(task) for task in req.json()["results"]]

    def add_task(self, task: Task):
        requests.post(
            urljoin(self._url, f"/api/projects/{task.project}/tasks/"),
            json=_serialize_task(task),
            headers=self._headers,
        )

    def update_task(self, task: Task):
        req = requests.put(
            urljoin(self._url, f"/api/tasks/{task.id}/"),
            json=_serialize_task(task),
            headers=self._headers,
        )

    def get_observations(
        self,
        task: Task | None = None,
        start_before: Time | None = None,
        start_after: Time | None = None,
        end_before: Time | None = None,
        end_after: Time | None = None,
        state: str | None = None,
    ) -> ObservationList:
        params = {}
        if start_before is not None:
            params["start_before"] = start_before.isot
        if start_after is not None:
            params["start_after"] = start_after.isot
        if end_before is not None:
            params["end_before"] = end_before.isot
        if end_after is not None:
            params["end_after"] = end_after.isot
        if state is not None:
            params["state"] = state
        if task is not None:
            params["task"] = task.id

        req = requests.get(urljoin(self._url, f"/api/observations/"), headers=self._headers, params=params)
        return ObservationList([Observation.model_validate(obs) for obs in req.json()["results"]])
