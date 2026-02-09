#!/usr/bin/env python3
import io
import os
import types
from typing import Any, get_origin, Union, get_args

import yaml
from nicegui import events, run, ui, app
from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from pydantic import BaseModel

from pyobs.robotic import Task

TASK_CONFIG = """
---
class: pyobs.robotic.Task
id: kochab
name: Kochab
priority: 1
duration: 2253
instrument: MONETS QHY
constraints:
  - class: pyobs.robotic.scheduler.constraints.AirmassConstraint
    max_airmass: 1.3
  - class: pyobs.robotic.scheduler.constraints.MoonSeparationConstraint
    min_distance: 30.0
merits:
  - class: pyobs.robotic.scheduler.merits.PerNightMerit
    count: 3
target:
  class: pyobs.robotic.scheduler.targets.SiderealTarget
  name: Kochab
  ra: 20.9406798056
  dec: -58.80578025804
script:
  class: pyobs.robotic.scripts.Script
"""

TASK2_CONFIG = """
---
class: pyobs.robotic.Task
id: fairall9
name: Fairall 9
priority: 1
duration: 2253
instrument: MONETS MORISOT
constraints:
  - class: pyobs.robotic.scheduler.constraints.AirmassConstraint
    max_airmass: 1.3
  - class: pyobs.robotic.scheduler.constraints.MoonSeparationConstraint
    min_distance: 30.0
merits:
  - class: pyobs.robotic.scheduler.merits.PerNightMerit
    count: 3
target:
  class: pyobs.robotic.scheduler.targets.SiderealTarget
  name: Fairall9
  ra: 20.9406798056
  dec: -58.80578025804
script:
  class: pyobs.robotic.scripts.Script
"""

os.environ["REPLICATE_API_TOKEN"] = "..."  # TODO: set your Replicate API token here


task_config = yaml.safe_load(TASK_CONFIG)
task1 = Task.model_validate(task_config)
task_config = yaml.safe_load(TASK2_CONFIG)
task2 = Task.model_validate(task_config)
tasks = {"kochab": task1, "fairall9": task2}

passwords = {"user1": "pass1", "user2": "pass2"}
unrestricted_page_routes = {"/login"}


@app.add_middleware
class AuthMiddleware(BaseHTTPMiddleware):
    """This middleware restricts access to all NiceGUI pages.

    It redirects the user to the login page if they are not authenticated.
    """

    async def dispatch(self, request: Request, call_next):
        if not app.storage.user.get("authenticated", False):
            if not request.url.path.startswith("/_nicegui") and request.url.path not in unrestricted_page_routes:
                return RedirectResponse(f"/login?redirect_to={request.url.path}")
        return await call_next(request)


@ui.page("/")
def main_page() -> None:
    def logout() -> None:
        app.storage.user.clear()
        ui.navigate.to("/login")

    nav()
    with ui.column().classes("absolute-center items-center"):
        ui.label(f'Hello {app.storage.user["username"]}!').classes("text-2xl")
        ui.button(on_click=logout, icon="logout").props("outline round")


def nav() -> None:
    with ui.header().classes("items-center justify-between"):
        ui.avatar("favorite_border")
        with ui.row().classes("max-sm:hidden"):
            with ui.link(target="/tasks"):
                ui.button("Tasks", icon="list").props("flat color=white")
            ui.button("Schedule", icon="calendar_month").props("flat color=white")
            ui.button("Observations", icon="camera").props("flat color=white")
        with ui.row().classes("sm:hidden"):
            ui.button(icon="list").props("flat color=white")
            ui.button(icon="calendar_month").props("flat color=white")
            ui.button(icon="camera").props("flat color=white")
        ui.button(icon="menu").props("flat color=white")


@ui.page("/login")
def login(redirect_to: str = "/") -> RedirectResponse | None:
    def try_login() -> None:  # local function to avoid passing username and password as arguments
        if passwords.get(username.value) == password.value:
            app.storage.user.update({"username": username.value, "authenticated": True})
            ui.navigate.to(redirect_to)  # go back to where the user wanted to go
        else:
            ui.notify("Wrong username or password", color="negative")

    if app.storage.user.get("authenticated", False):
        return RedirectResponse("/")
    with ui.card().classes("absolute-center"):
        username = ui.input("Username").on("keydown.enter", try_login)
        password = ui.input("Password", password=True, password_toggle_button=True).on("keydown.enter", try_login)
        ui.button("Log in", on_click=try_login)
    return None


@ui.page("/tasks")
def tasks_page() -> None:
    nav()
    ui.label("Tasks")
    data = [t.model_dump() for t in tasks.values()]
    table = ui.table(
        rows=data,
        columns=[
            {"name": "id", "label": "ID", "field": "id"},
            {"name": "name", "label": "Name", "field": "name"},
            {"name": "target", "label": "Target", ":field": "row => row.target.name"},
        ],
        column_defaults={
            "align": "left",
            "headerClasses": "uppercase text-primary",
        },
    ).classes("w-full")
    with table.add_slot("body-cell-id"):
        with table.cell("id"):
            ui.link().props(":href=\"'/tasks/' + props.value + '/show'\" :innerHTML=props.value")


def task_nav(task_id: str, active: str) -> None:
    links = {
        "show": {"icon": "visibility", "label": "Show"},
        "edit": {"icon": "edit", "label": "Edit"},
        "schedule": {"icon": "calendar_month", "label": "Schedule"},
        "observations": {"icon": "camera", "label": "Observations"},
    }

    for name, link in links.items():
        color = "red" if name == active else "black"
        with ui.link(target=f"/tasks/{task_id}/{name}"):
            ui.button(link["label"], icon=link["icon"]).props(f"flat color={color}")


@ui.page("/tasks/{task_id}/{page}")
def task_page(task_id: str, page: str) -> None:
    nav()
    with ui.column().classes("w-full items-center"):
        task = tasks[task_id]
        ui.label(f"Task {task.name} (ID: {task.id})").classes("text-h5")
        with ui.row().classes("gap-16"):
            with ui.column().classes("w-50 items-stretch"):
                task_nav(task_id, page)
            with ui.column().classes("w-100 items-stretch"):
                if page == "show":
                    show_task_page(task)
                elif page == "edit":
                    edit_task_page(task)
                elif page == "schedule":
                    schedule_task_page(task)
                elif page == "observations":
                    observations_task_page(task)

        # build_ui(task)
    # ui.input(label="Task name").bind_value(task, "name")
    # ui.input(label="Task ID").bind_value(task, "id")


def show_task_page(task: Task) -> None:
    with ui.row():
        ui.label("Priority:").classes("text-bold")
        ui.label(f"{task.priority}")
    with ui.row():
        ui.label("Duration:").classes("text-bold")
        ui.label(f"{task.duration} sec")


def edit_task_page(task: Task) -> None:
    with ui.card():
        ui.label("General").classes("text-bold")
        ui.input("ID").classes("w-80 mx-auto")
        ui.input("Name").classes("w-80 mx-auto")
        ui.number("Priority", format="%d").classes("w-80 mx-auto")
        ui.number("Duration", format="%d", suffix="sec").classes("w-80 mx-auto")
    with ui.card():
        ui.label("Target").classes("text-bold")
        ui.input("Name").classes("w-80 mx-auto")
        ui.input("RA").classes("w-80 mx-auto")
        ui.input("Dec").classes("w-80 mx-auto")


def schedule_task_page(task: Task) -> None:
    ui.label("Schedule Task")


def observations_task_page(task: Task) -> None:
    ui.label("Observations Task")


def is_type(obj: Any, type: Any) -> bool:
    origin = get_origin(obj)
    if origin is None:
        return obj is type
    if origin is type:
        return True
    if origin in (Union, types.UnionType):
        return any(is_type(a, type) for a in get_args(obj))
    return False


def build_ui(model: BaseModel) -> None:
    for name, field in model.model_fields.items():
        print(name, field.annotation, get_origin(field.annotation))
        if is_type(field.annotation, str) or is_type(field.annotation, Any):
            ui.input(label=name).bind_value(model, name)
        elif is_type(field.annotation, float):
            ui.number(label=name, format="%.2f").bind_value(model, name)
        elif is_type(field.annotation, int):
            ui.number(label=name, format="%d").bind_value(model, name)
        elif is_type(field.annotation, list):
            ui.label(f"LIST {name}")
        # print(field.annotation)
        # if field.annotation is list or get_origin(field.annotation) is list:
        #    print("LIST")


ui.run(storage_secret="THIS_NEEDS_TO_BE_CHANGED")
