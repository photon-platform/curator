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
from datetime import date


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

    def update_changelog(self, version: str, description: str) -> None:
        changelog_file = self.root_path / "CHANGELOG.rst"
        if not changelog_file.exists():
            print(f"No CHANGELOG.rst file found at {changelog_file}!")
            return
        template = f"""\

{ version }
{ '-' * len(version) }

:init: { date.today().strftime("%Y.%j") } 
:merge:
:pub:

  { description }

- actions"""

        changelog_file.write_text(
            changelog_file.read_text()
            + template
        )

    def merge_to_main(self, branch_name: str, commit_message: str) -> None:
        main_branch = self.repo.heads["main"]
        dev_branch = self.repo.heads[branch_name]
        self.repo.git.checkout("main")
        self.repo.git.merge(dev_branch, m=commit_message)
        return True, f"Merged {branch_name} to main"

    def current_version(self):
        namespace, module = self.discover()
        if module is None:
            return

        return self.get_version(module)

    def create_release_branch(self, release_version: str, description: str) -> None:
        namespace, module = self.discover()

        if module is None:
            return False, "Module not found"

        current_version = self.get_version(module)

        # Create and checkout the release branch
        self.repo.git.checkout("-b", release_version)
        print(self.branches())

        self.set_version(module, release_version)

        self.update_changelog(release_version, description)

        self.repo.git.add(
            str(module / "__init__.py"), str(self.root_path / "CHANGELOG.rst")
        )
        self.repo.git.commit("-m", f"init release {release_version}\n{description}")

        # Set upstream and push the new branch
        try:
            self.repo.git.push("--set-upstream", "origin", release_version)
            #  print(f"Successfully pushed and set upstream for branch {release_version}")
        except Exception as e:
            #  print(f"Error pushing branch: {str(e)}")
            return False, f"Failed to push branch: {str(e)}"

        return True, f"\n{release_version} set and pushed to remote"
