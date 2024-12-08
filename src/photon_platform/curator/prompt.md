the following are python modules from photon_platform.curator

the main function currently is to manage a git repo


./app.py
```
"""
CuratorApp
"""
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Button, Input, Label
from textual.binding import Binding

from rich import inspect, print
from rich.text import Text

from datetime import datetime
from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape

from .curator import Curator
from photon_platform.formulator import load_blueprint, FormulatorModal, Formulator


class CuratorApp(App):
    CSS_PATH = "app.css"
    TITLE = "PHOTON • curator"
    SUBTITLE = Path.cwd()
    BINDINGS = [
        Binding("c", "create_release_branch", "create release branch"),
        Binding("m", "merge_release_branch", "merge release branch"),
        Binding("ctrl-p", "screenshot", "screenshot", show=False),
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

        import os

        # Get the directory containing the current file
        current_dir = os.path.dirname(__file__)

        # Construct the full path to the YAML file
        yaml_file_path = os.path.join(current_dir, "create_release_branch.yaml")

        # Now load the blueprint using the full path
        blueprint = load_blueprint(yaml_file_path)

        def get_context(context) -> None:
            #  self.curator.create_release_branch(context["release_version"], context["release_branch_name"])
            inspect(context)
            self.exit(context)

        self.push_screen(FormulatorModal(blueprint), get_context)



        #  self.query_one("#branches").value = str(self.curator.repo.branches)
        #  self.query_one("#active_branch").value = str(self.curator.repo.active_branch)
        #  self.query_one("#tags").value = str(self.curator.repo.tags)


    def action_screenshot(self, path: str = "./") -> None:

        log_stamp = self.query_one("#log").value
        filename = f"log/{log_stamp}.svg"
        path = self.save_screenshot(filename, path)

        message = Text.assemble("Screenshot saved to ", (f"'{path}'", "bold green"))
        #  print(message)
        self.bell()

def run() -> None:
    app = CuratorApp()
    result = app.run()
    inspect(result)
```


./curator.py
```
"""
Curator
=======

    # Example usage
    curator = Curator('.')
    curator.create_release_branch('1.0.0', 'release-1.0.0')
    curator.merge_to_main('release-1.0.0', 'Release 1.0.0')

"""
from git import Repo
from pathlib import Path
from git.exc import InvalidGitRepositoryError
from github import Github
import toml
import os
from rich import print, inspect


class Curator:
    def __init__(self, repo_path: str = "."):
        try:
            self.repo = Repo(repo_path, search_parent_directories=True)
            #  inspect(self.repo)
            self.root_path = Path(self.repo.git.rev_parse("--show-toplevel"))
        except InvalidGitRepositoryError:
            print(f"No git repository found at {Path(repo_path).resolve()}!")
            raise
        self.pyproject_toml = self.load_pyproject_toml()
        self.github_client = Github(os.getenv("GITHUB_TOKEN"))
        self.github_repo = self.get_github_repo()
        #  TODO change log


    def get_github_repo(self):
        #  repo = self.github_client.get_repo(f"geometor/{self.repo.name}")
        #  return repo
        pass

    def load_pyproject_toml(self):
        pyproject_path = self.root_path / "pyproject.toml"
        if pyproject_path.exists():
            with open(pyproject_path, "r", encoding="utf-8") as file:
                return toml.load(file)
        else:
            print(f"No pyproject.toml file found at {pyproject_path}!")
            return None

    def branches(self) -> dict:
        branches = {}
        for branch in self.repo.branches:
            if branch == self.repo.active_branch:
                branches[branch] = True
            else:
                branches[branch] = False

        return branches

    def discover(self) -> tuple[Path, Path]:
        source_path = self.root_path / "src"
        if not source_path.exists():
            print(f"No source directory found at {source_path}!")
            return None, None

        first_child = next(source_path.iterdir())

        if not (first_child / "__init__.py").exists():
            # This is a namespace, check the first child
            namespace = first_child
            module = next(namespace.iterdir())
        else:
            # There is no namespace, this is a module
            namespace = None
            module = first_child

        if not (module / "__init__.py").exists():
            print(f"No __init__.py file found in module at {module}!")
            return None, None

        return namespace, module

    def get_version(self, module: Path) -> str:
        init_file = module / "__init__.py"
        lines = init_file.read_text().splitlines()
        for line in lines:
            if line.startswith("__version__"):
                return line.split("=")[1].strip().strip("'")
        return None

    def set_version(self, module: Path, version: str) -> None:
        init_file = module / "__init__.py"
        lines = init_file.read_text().splitlines()
        for i, line in enumerate(lines):
            if line.startswith("__version__"):
                lines[i] = f"__version__ = '{version}'"
        init_file.write_text("\n".join(lines) + "\n")

    def update_changelog(self, version: str) -> None:
        changelog_file = self.root_path / "CHANGELOG.md"
        if not changelog_file.exists():
            print(f"No CHANGELOG.md file found at {changelog_file}!")
            return
        changelog_file.write_text(
            changelog_file.read_text()
            + f"\n## {version}\n\n- Placeholder for changes\n"
        )

    def merge_to_main(self, branch_name: str, commit_message: str) -> None:
        main_branch = self.repo.heads["main"]
        dev_branch = self.repo.heads[branch_name]
        self.repo.git.checkout("main")
        self.repo.git.merge(dev_branch, m=commit_message)
        print(f"Merged {branch_name} to main")

    def current_version(self):
        namespace, module = self.discover()
        if module is None:
            return

        return self.get_version(module)

    def create_release_branch(
        self, release_version: str, release_branch_name: str
    ) -> None:
        namespace, module = self.discover()
        if module is None:
            return

        current_version = self.get_version(module)

        self.set_version(module, release_version)

        # Append a placeholder to the CHANGELOG.md
        self.update_changelog(release_version)

        # Commit the changes
        self.repo.git.add(
            str(module / "__init__.py"), str(self.root_path / "CHANGELOG.md")
        )
        self.repo.git.commit("-m", f"Start release {release_version}")

        return f"Release branch {release_branch_name} created and initialized for release {release_version}"
```


# INSTRUCTIONS

The major role for Curator will be to manage development branches

the implementation is not finished - let's work to complete




