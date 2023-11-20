## src/photon_platform/curator/__init__.py

```py
"""
curator
=======

PHOTON platform
---------------



"""
__author__ = "PHOTON platform"
__maintainer__ = "PHOTON platform"
__email__ = "github@phiarchitect.com"
__version__ = "0.0.1"
__licence__ = "MIT"

```

## src/photon_platform/curator/__main__.py

```py
"""The package entry point into the application."""

from .app import run

if __name__ == "__main__":
    run()
```

## src/photon_platform/curator/_app.py

```py
"""
run the main app
"""
from .curator import Curator


def run() -> None:
    reply = Curator().run()
    print(reply)

```

## src/photon_platform/curator/app.py

```py
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
from photon_platform.formulator import load_blueprint, FormulatorModal


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

        blueprint = load_blueprint("create_release_branch.yaml")
        context = self.push_screen(FormulatorModal(validation_errors))
        self.curator.create_release_branch(**context)


        self.query_one("#branches").value = str(self.curator.repo.branches)
        self.query_one("#active_branch").value = str(self.curator.repo.active_branch)
        self.query_one("#tags").value = str(self.curator.repo.tags)


    def action_screenshot(self, path: str = "./") -> None:

        log_stamp = self.query_one("#log").value
        filename = f"log/{log_stamp}.svg"
        path = self.save_screenshot(filename, path)

        message = Text.assemble("Screenshot saved to ", (f"'{path}'", "bold green"))
        #  print(message)
        self.bell()

def run() -> None:
    app = CuratorApp()
    app.run()

```

## src/photon_platform/curator/curator.py

```py
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
            inspect(self.repo)
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

## src/photon_platform/curator/gather.py

```py
import os
from bs4 import BeautifulSoup
import markdownify
import subprocess
import shutil

def get_git_root(path='.'):
    """
    Find the root directory of the git repository.
    """
    git_root = subprocess.run(['git', 'rev-parse', '--show-toplevel'], stdout=subprocess.PIPE, text=True, check=True, cwd=path).stdout.strip()
    return git_root

def create_clerk_directory(directory):
    """
    Create the .clerk directory if it doesn't exist.
    """
    if not os.path.exists(directory):
        os.makedirs(directory)

def run_sphinx_build(src, dest):
    """
    Run sphinx-build to generate singlehtml documentation.
    """
    subprocess.run(['sphinx-build', '-b', 'singlehtml', src, dest], check=True)

def clean_directory_except_index_html(directory):
    """
    Remove all files except index.html in the given directory.
    """
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path) and filename != 'index.html':
            os.remove(file_path)


def gather_source_code(src_directory, output_file):
    """
    Gathers all the source code from the src directory into a single markdown file.
    """
    # List to store file paths
    files = []

    # Walk through the directory and add file paths to the list
    for root, dirs, filenames in os.walk(src_directory):
        for filename in filenames:
            if filename.endswith('.py'):
                files.append(os.path.join(root, filename))

    # Sort the files to ensure __init__.py is at the beginning
    files.sort(key=lambda x: (not x.endswith('__init__.py'), x))

    # Open the output file
    with open(output_file, 'w') as md_file:
        for file_path in files:
            # Write the file path as a header in the markdown file
            md_file.write(f'## {file_path}\n\n```py\n')

            # Open and read the content of the file
            with open(file_path, 'r') as f:
                content = f.read()

            # Write the content to the markdown file
            md_file.write(content)
            md_file.write('\n```\n\n')

    print(f"Source code gathered into {output_file}")


def extract_div_convert_to_markdown(html_file_path, output_markdown_file):
    """
    Extracts the div with class 'document' from an HTML file and converts it to Markdown.

    Args:
    html_file_path (str): Path to the HTML file.
    output_markdown_file (str): Path for the output Markdown file.
    """
    # Read the HTML file
    with open(html_file_path, 'r', encoding='utf-8') as file:
        html_content = file.read()

    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find the div with class 'document'
    document_div = soup.find('div', class_='document')

    # Convert the HTML of the document div to Markdown
    markdown_content = markdownify.markdownify(str(document_div), heading_style="ATX")

    # Write the Markdown content to the output file
    with open(output_markdown_file, 'w', encoding='utf-8') as md_file:
        md_file.write(markdown_content)

    print(f"Markdown file created at {output_markdown_file}")


#  if __name__ == "__main__":
    #  # Example usage
    #  gather_source_code('src', '.clerk/src.md')
    #  extract_div_convert_to_markdown('.clerk/doc/index.html', '.clerk/doc/main.md')

if __name__ == "__main__":
    # Change to Git root directory
    git_root = get_git_root()
    os.chdir(git_root)

    # Create .clerk and .clerk/doc directories
    clerk_directory = os.path.join(git_root, '.clerk')
    clerk_doc_directory = os.path.join(clerk_directory, 'doc')
    create_clerk_directory(clerk_directory)
    create_clerk_directory(clerk_doc_directory)

    # Run sphinx-build
    run_sphinx_build('docsrc', clerk_doc_directory)

    # Clean up .clerk/doc directory
    clean_directory_except_index_html(clerk_doc_directory)

    # Gather source code and convert documentation to Markdown
    gather_source_code('src', os.path.join(clerk_directory, 'src.md'))
    extract_div_convert_to_markdown(os.path.join(clerk_doc_directory, 'index.html'), os.path.join(clerk_directory, 'doc', 'main.md'))


```

## src/photon_platform/curator/modal.py

```py
from textual.app import App, ComposeResult
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Input,
    Label,
    Checkbox,
    RadioSet,
    RadioButton,
    Select,
    Static,
    Switch,
    OptionList,
    Header,
    Footer,
)
from textual.containers import Grid, Vertical, Horizontal

class AlertScreen(ModalScreen):

    def __init__(self, message: str):
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(self._message, id="message"),
            Button("OK", id="ok"),
            id="alert",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            self.app.exit()
        else:
            self.app.pop_screen()


class ErrorScreen(ModalScreen):
    
    def __init__(self, errors: list):
        super().__init__()
        self._errors = errors

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(str(self._errors), id="errors"),
            Button("OK", variant="error", id="ok"),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit":
            self.app.exit()
        else:
            self.app.pop_screen()


```

