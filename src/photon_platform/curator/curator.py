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


class Curator:
    def __init__(self, repo_path: str = "."):
        try:
            self.repo = Repo(repo_path, search_parent_directories=True)
            self.root_path = Path(self.repo.git.rev_parse("--show-toplevel"))
        except InvalidGitRepositoryError:
            print(f"No git repository found at {Path(repo_path).resolve()}!")
            raise

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
