"""
CuratorApp
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Button, Input, Label
from textual.binding import Binding

import os
from rich import inspect, print
from rich.text import Text

from datetime import datetime
from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape

from .curator import Curator
from .modal import AlertScreen, ErrorScreen  # Import modal screens
from photon_platform.formulator import load_blueprint, FormulatorModal, Formulator


class CuratorApp(App):
    CSS_PATH = "app.css"
    TITLE = "PHOTON • curator"
    SUBTITLE = Path.cwd()
    BINDINGS = [
        Binding("c", "create_release_branch", "create release branch"),
        Binding("m", "merge_release_branch", "merge release branch"),
        #  Binding("ctrl-p", "screenshot", "screenshot", show=False),
        Binding("q", "quit", "quit"),
    ]

    def __init__(self):
        super().__init__()
        self.curator = Curator()

    def compose(self) -> ComposeResult:
        namespace, module = self.curator.discover()
        yield Header()
        yield Footer()
        yield Container(
            Label("CWD:"),
            Static(str(Path.cwd())),
            Label("DESC:"),
            Static(self.curator.repo.description, id="desc"),
            Label("BRANCHES:"),
            Static(str(self.curator.branches()), id="branches"),
            Label("ACTIVE:"),
            Static(str(self.curator.repo.active_branch), id="active_branch"),
            Label("TAGS:"),
            Static(str(self.curator.repo.tags), id="tags"),
            Label("VERSION:"),
            Static(str(self.curator.current_version()), id="version"),
            #  id="details",
        )

    def action_create_release_branch(self):

        # Get the directory containing the current file
        current_dir = os.path.dirname(__file__)

        # Construct the full path to the YAML file
        yaml_file_path = os.path.join(current_dir, "create_release_branch.yaml")

        # Now load the blueprint using the full path
        blueprint = load_blueprint(yaml_file_path)

        def get_context(context: dict) -> None:
            success = False
            message = "No action taken."
            if "release_version" in context:
                success, message = self.curator.create_release_branch(**context)

            # Then update UI and notify based on the result
            if success:
                self.query_one("#branches").update(str(self.curator.branches()))
                self.query_one("#active_branch").update(
                    str(self.curator.repo.active_branch)
                )
                self.query_one("#tags").update(str(self.curator.repo.tags))
                self.query_one("#version").update(str(self.curator.current_version()))
                self.notify(message, title="Success", severity="information")
            else:
                self.notify(message, title="Error", severity="error")

        self.push_screen(FormulatorModal(blueprint), get_context)

    def action_merge_release_branch(self):
        # Get the directory containing the current file
        current_dir = os.path.dirname(__file__)

        # Construct the full path to the YAML file
        yaml_file_path = os.path.join(current_dir, "merge_release_branch.yaml")

        # Now load the blueprint using the full path
        blueprint = load_blueprint(yaml_file_path)

        def get_context(context: dict) -> None:
            success = False
            message = "No action taken."
            if "branch_name" in context:
                success, message = self.curator.merge_to_main(**context)

            # Dismiss the modal first
            self.dismiss()

            # Then update UI and notify based on the result
            if success:
                self.query_one("#branches").update(str(self.curator.branches()))
                self.query_one("#active_branch").update(
                    str(self.curator.repo.active_branch)
                )
                self.query_one("#tags").update(str(self.curator.repo.tags))
                # Version doesn't change on merge, so no need to update it here
                self.notify(message, title="Success", severity="information")
            else:
                self.notify(message, title="Error", severity="error")

        self.push_screen(FormulatorModal(blueprint), get_context)

    #  def action_screenshot(self, path: str = "./") -> None:

    #  log_stamp = self.query_one("#log").value
    #  filename = f"log/{log_stamp}.svg"
    #  path = self.save_screenshot(filename, path)

    #  message = Text.assemble("Screenshot saved to ", (f"'{path}'", "bold green"))
    #  #  print(message)
    #  self.bell()


def run() -> None:
    app = CuratorApp()
    result = app.run()
    inspect(result)
