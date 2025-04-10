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

    def discover(self) -> tuple[Path | None, Path | None]:
        """
        Discovers the source directory and main module path based on pyproject.toml,
        prioritizing [tool.setuptools.dynamic].version.attr.
        """
        if not self.pyproject_toml:
            print("pyproject.toml not loaded or not found.")
            return None, None

        source_dir_name = "src"  # Default, can be overridden by find config
        module_python_path = None # e.g., "photon_platform.curator"

        # --- Determine Source Directory Name ---
        try:
            # Check setuptools.packages.find first for 'where'
            find_config = self.pyproject_toml.get("tool", {}).get("setuptools", {}).get("packages", {}).get("find", {})
            if find_config and "where" in find_config and isinstance(find_config["where"], list) and find_config["where"]:
                source_dir_name = find_config["where"][0] # Use the first directory listed
                print(f"Using source directory '{source_dir_name}' from [tool.setuptools.packages.find].where")
            # We could potentially check poetry's 'from' here too if needed as another fallback
        except Exception as e:
            print(f"Could not parse [tool.setuptools.packages.find].where, using default '{source_dir_name}': {e}")


        # --- Determine Module Python Path ---
        # 1. Prioritize [tool.setuptools.dynamic].version.attr
        try:
            dynamic_config = self.pyproject_toml.get("tool", {}).get("setuptools", {}).get("dynamic", {})
            if "version" in dynamic_config and isinstance(dynamic_config["version"], dict):
                version_attr = dynamic_config["version"].get("attr")
                if isinstance(version_attr, str) and "." in version_attr:
                    # version_attr is like "photon_platform.curator.__version__"
                    # We need the part before the last dot: "photon_platform.curator"
                    module_python_path = version_attr.rsplit('.', 1)[0]
                    print(f"Found module path from [tool.setuptools.dynamic].version.attr: {module_python_path}")
        except Exception as e:
            print(f"Could not parse [tool.setuptools.dynamic].version.attr: {e}")
            # Continue to next method

        # 2. Fallback: Use [project.name] if module path still not found
        #    (Less reliable for finding the *exact* module path, but better than nothing)
        if not module_python_path:
            print("Module path not found via dynamic version attr, falling back to [project.name]...")
            try:
                project_name = self.pyproject_toml.get("project", {}).get("name")
                if project_name:
                    # Convert project name (e.g., "photon-platform-curator")
                    # to a potential Python path (e.g., "photon_platform_curator" or "photon_platform.curator")
                    # This requires making assumptions about the structure.
                    potential_path = project_name.replace("-", "_")

                    # --- Basic Validation of inferred path ---
                    # Construct the potential filesystem path for validation
                    temp_source_path = self.root_path / source_dir_name
                    temp_module_path_parts = potential_path.replace('.', '/').split('/')
                    temp_full_path = temp_source_path.joinpath(*temp_module_path_parts)

                    # Check if the directory and its __init__.py exist
                    if temp_full_path.is_dir() and (temp_full_path / "__init__.py").is_file():
                        module_python_path = potential_path # Use the derived path
                        print(f"Inferred and validated module path from [project.name]: {module_python_path}")
                    else:
                        print(f"Could not validate inferred path '{temp_full_path}' from [project.name].")
                        # Attempt to find the module within the includes from setuptools.find
                        find_config = self.pyproject_toml.get("tool", {}).get("setuptools", {}).get("packages", {}).get("find", {})
                        includes = find_config.get("include", [])
                        if includes:
                             # Example: includes = ["photon_platform"], project_name = "photon-platform-curator"
                             # We might infer module is "curator" inside "photon_platform"
                             top_level_package = includes[0].replace('/','.') # e.g., "photon_platform"
                             module_part = project_name.split(top_level_package.replace('_','-'))[-1].strip('-') # e.g. "curator"
                             if module_part:
                                 potential_path = f"{top_level_package}.{module_part}"
                                 temp_module_path_parts = potential_path.replace('.', '/').split('/')
                                 temp_full_path = temp_source_path.joinpath(*temp_module_path_parts)
                                 if temp_full_path.is_dir() and (temp_full_path / "__init__.py").is_file():
                                     module_python_path = potential_path
                                     print(f"Inferred and validated module path using [project.name] and includes: {module_python_path}")


            except Exception as e:
                 print(f"Could not parse [project.name] or validate path: {e}")


        # --- Final Checks and Path Construction ---
        if not module_python_path:
            print("Could not determine module Python path from pyproject.toml.")
            print("Checked: [tool.setuptools.dynamic].version.attr, [project.name]")
            return None, None

        # Construct filesystem paths using the determined source_dir_name and module_python_path
        source_path = self.root_path / source_dir_name
        if not source_path.is_dir():
            print(f"Source directory '{source_dir_name}' determined from pyproject.toml not found at {source_path}")
            return None, None

        # Convert module Python path (e.g., "photon_platform.curator")
        # into path components relative to the source directory.
        package_path_parts = module_python_path.replace('.', '/').split('/')

        module_path = source_path.joinpath(*package_path_parts)
        namespace_path = None

        # Determine namespace path if applicable (parent dir relative to source_path)
        if len(package_path_parts) > 1 and module_path.parent != source_path:
             namespace_path = module_path.parent


        # Validate the final module path
        if not module_path.is_dir():
            print(f"Determined module path '{module_path}' does not exist or is not a directory.")
            return None, None

        init_file = module_path / "__init__.py"
        if not init_file.is_file():
            print(f"No __init__.py file found in determined module directory: {module_path}")
            return None, None

        print(f"Discovered namespace: {namespace_path}, module: {module_path}") # Debug print
        return namespace_path, module_path

    def get_version(self, module: Path) -> str | None:
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

    def create_tag(self, tag_name: str, message: str) -> tuple[bool, str]:
        """Creates an annotated tag and pushes it to origin."""
        if self.repo.active_branch.name != 'main':
            return False, "Must be on 'main' branch to create a release tag."

        try:
            # Create annotated tag
            self.repo.create_tag(tag_name, message=message, force=False) # force=False prevents overwriting existing tags
            # Push the tag to origin
            self.repo.git.push("origin", tag_name)
            return True, f"Tag '{tag_name}' created and pushed successfully."
        except Exception as e:
            # Catch potential errors like tag already exists or push failure
            return False, f"Failed to create or push tag '{tag_name}': {str(e)}"
