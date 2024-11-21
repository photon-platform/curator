"""
GitHub repository utility - fetches repo info and creates RST documentation
"""
from rich import print
import subprocess
import json
from pathlib import Path
from datetime import datetime
from slugify import slugify
import base64
import requests


def run_gh_command(args: list, fields: str = None) -> dict:
    """Run GitHub CLI command and return JSON output."""
    try:
        cmd = ["gh"] + args
        if fields:
            cmd.extend(["--json", fields])
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,  # This will raise CalledProcessError if command fails
        )
        if not result.stdout.strip():
            raise ValueError("Empty response from GitHub CLI")
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"[red]Error running gh command:[/red] {e}")
        print(f"stderr: {e.stderr}")
        raise
    except json.JSONDecodeError as e:
        print(f"[red]Error parsing gh output:[/red] {e}")
        print(f"stdout: {result.stdout}")
        raise


def get_repo_data(repo: str) -> dict:
    """Fetch repository metadata from GitHub."""
    # Get repo info with specific fields
    repo_fields = "name,nameWithOwner,owner,description,homepageUrl,createdAt,updatedAt,stargazerCount,forkCount,primaryLanguage,licenseInfo,url,sshUrl"
    repo_data = run_gh_command(["repo", "view", repo], repo_fields)

    print('repo_data:',repo_data)

    # Get latest release if any
    try:
        release = run_gh_command(["release", "view", "--repo", repo], "tagName")
    except:
        release = None

    response = {
        "name": repo_data["name"],
        "nameWithOwner": f"{repo_data['nameWithOwner']}",
        "owner": repo_data["owner"],
        "description": repo_data["description"],
        "homepage": repo_data["homepageUrl"],
        "created_at": datetime.fromisoformat(repo_data["createdAt"].rstrip("Z")),
        "updated_at": datetime.fromisoformat(repo_data["updatedAt"].rstrip("Z")),
        "stars": repo_data["stargazerCount"],
        "forks": repo_data["forkCount"],
        "language": repo_data["primaryLanguage"]["name"]
        if repo_data["primaryLanguage"]
        else None,
        "license": repo_data["licenseInfo"]["name"]
        if repo_data["licenseInfo"]
        else None,
        "latest_release": release["tagName"] if release else None,
        "url": repo_data["url"],
        "sshUrl": repo_data["sshUrl"],
    }
    #  print(response)
    return response


def create_include_files(repo_dir: Path):
    """Create include files for analysis sections."""
    includes = {
        "notes.rst": """\
notes
-----

""",
    }

    for filename, content in includes.items():
        include_path = repo_dir / filename
        include_path.write_text(content)
        print(f"Created include file: {include_path}")


def format_rst(data: dict, readme_content: str = "") -> str:
    """Format repository data as RST document."""
    # Create slug from repo name
    slug = slugify(data["nameWithOwner"])

    rst = f"""\
.. _{slug}:

{data['nameWithOwner']}
{'=' * len(data['nameWithOwner'])}

:description: {data['description'] or 'N/A'}
:url: {data['url']}
:sshUrl: {data['sshUrl']}
:homepage: {data['homepage'] or 'N/A'}
:created_at: {data['created_at'].strftime('%Y-%m-%d')}
:license: {data['license'] or 'N/A'}
:latest_release: {data['latest_release'] or 'N/A'}

.. toctree::
   :maxdepth: 1

   {data["readme_filename"]}

.. include:: notes.rst
"""
    return rst.strip()


def fetch_and_save_readme(data: dict, repo_dir: Path) -> tuple[bool, str]:
    """Fetch and save README file, trying MD then RST format."""
    print("get README")
    # Try markdown first
    try:
        readme_url = f"https://raw.githubusercontent.com/{data['nameWithOwner']}/main/README.md"
        response = requests.get(readme_url)
        response.raise_for_status()
        readme_path = repo_dir / "README.md"
        content = "# README.md\n\n" + response.text
        readme_path.write_text(content)
        return True, "README.md"
    except requests.RequestException:
        # Try RST if MD fails
        try:
            readme_url = f"https://raw.githubusercontent.com/{data['nameWithOwner']}/main/README.rst"
            response = requests.get(readme_url)
            response.raise_for_status()
            readme_path = repo_dir / "README.rst"
            content = "README.rst\n-----------\n\n" + response.text
            readme_path.write_text(content)
            return True, "README.rst"
        except requests.RequestException as e:
            print(f"[yellow]Warning: Could not fetch either README:[/yellow] {e}")
            return False, ""


def save_reference(repo: str, output_dir: str = ".") -> Path:
    """Save repository metadata as RST."""
    data = get_repo_data(repo)


    # Create repo directory using owner_repo format
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    repo_dir = output_path / slugify(data["nameWithOwner"])
    repo_dir.mkdir(parents=True, exist_ok=True)

    # Create include files
    create_include_files(repo_dir)

    # Fetch and save README
    #  "readme_url": f"https://raw.githubusercontent.com/{repo}/main/README",
    readme_exists, readme_filename = fetch_and_save_readme(data, repo_dir)
    data["readme_filename"] = readme_filename

    # Generate RST content
    rst_content = format_rst(data, repo_dir)

    # Add README to toctree if it exists
    #  if readme_exists:
    #  rst_content += f"\n   {readme_filename}"

    # Save index.rst
    index_path = repo_dir / "index.rst"
    index_path.write_text(rst_content)
    print(f"Created RST file: {index_path}")

    return index_path


def main():
    """Main entry point for command line usage."""
    import sys

    if len(sys.argv) == 2:
        repo = sys.argv[1]
    else:
        repo = input("Please enter the GitHub repository (e.g. owner/repo): ").strip()

    if not repo or "/" not in repo:
        print("[red]Invalid repository format. Use owner/repo format.[/red]")
        sys.exit(1)

    try:
        index_path = save_reference(repo)
        print("\n[green]✓ Successfully saved reference:[/green]")
        print(f"  RST: {index_path}")
    except Exception as e:
        print(f"[red]Error processing GitHub repository:[/red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
