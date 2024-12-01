import os
from bs4 import BeautifulSoup
import markdownify
import subprocess
import shutil
import toml


def get_git_root(path="."):
    """
    Find the root directory of the git repository.
    """
    git_root = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        stdout=subprocess.PIPE,
        text=True,
        check=True,
        cwd=path,
    ).stdout.strip()
    return git_root


def get_project_name(git_root):
    """
    Get the project name from pyproject.toml file.
    """
    pyproject_path = os.path.join(git_root, "pyproject.toml")
    if os.path.exists(pyproject_path):
        with open(pyproject_path, "r") as file:
            pyproject_data = toml.load(file)
            return pyproject_data.get("project", {}).get("name")
    return None


def create_clerk_directory(directory):
    """
    Create the .clerk directory if it doesn't exist.
    """
    if not os.path.exists(directory):
        os.makedirs(directory)


def ensure_parent_path_exists(file_path):
    """
    Ensure that the parent path of the given file exists. If not, create it.
    """
    parent_directory = os.path.dirname(file_path)
    if not os.path.exists(parent_directory):
        os.makedirs(parent_directory, exist_ok=True)


def gen_tree(path, dest):
    """
    Generate a tree structure of the given path and output to destination file.
    """
    result = subprocess.run(
        ["tree", "--gitignore", path], capture_output=True, text=True, check=True
    )
    ensure_parent_path_exists(dest)
    with open(dest, "w") as file:
        file.write(result.stdout)


def run_sphinx_build(src, dest):
    """
    Run sphinx-build to generate singlehtml documentation.
    """
    subprocess.run(
        ["sphinx-build", "-b", "singlehtml", "-D", "html_permalinks=''", src, dest],
        check=True,
    )


def remove_header_links(html_content) -> str:
    """
    Removes all <a> tags with class 'headerlink' from the HTML content.

    returns:
    str: Modified HTML content with header links removed.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    for header_link in soup.find_all("a", class_="headerlink"):
        header_link.decompose()
    return str(soup)


def clean_directory_except_index_html(directory):
    """
    Remove all files except index.html in the given directory.
    """
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path) and filename != "index.html":
            os.remove(file_path)


def gather_source_code(src_directory, output_file):
    """
    Gathers all the source code from the src directory into a single markdown file.
    """

    def file_sort_key(filename):
        if filename == "__init__.py":
            return (0, filename)
        elif filename.startswith("__") and filename.endswith(".py"):
            return (1, filename)
        else:
            return (2, filename)

    with open(output_file, "w") as md_file:
        for root, dirs, filenames in os.walk(src_directory):
            dirs.sort()  # Ensure directories are processed in order
            py_files = [
                f
                for f in filenames
                if f.endswith(".py") or f.endswith(".j2") or f.endswith(".css")
            ]
            py_files.sort(key=file_sort_key)
            for filename in py_files:
                if filename.endswith(".py"):
                    file_type = "py"
                if filename.endswith(".j2"):
                    file_type = "jinja"
                if filename.endswith(".md"):
                    file_type = "markdown"
                if filename.endswith(".css"):
                    file_type = "css"
                file_path = os.path.join(root, filename)
                md_file.write(f"## {file_path}\n\n```{file_type}\n")
                with open(file_path, "r") as f:
                    content = f.read()
                md_file.write(content)
                md_file.write("\n```\n\n")

    print(f"Source code gathered into {output_file}")


def extract_div_convert_to_markdown(html_file_path, output_markdown_file):
    """
    Extracts the div with class 'document' from an HTML file and converts it to Markdown.

    Args:
    html_file_path (str): Path to the HTML file.
    output_markdown_file (str): Path for the output Markdown file.
    """
    with open(html_file_path, "r", encoding="utf-8") as file:
        html_content = file.read()

    cleaned_html_content = remove_header_links(html_content)
    soup = BeautifulSoup(cleaned_html_content, "html.parser")
    document_div = soup.find("div", class_="document")
    markdown_content = markdownify.markdownify(str(document_div), heading_style="ATX")

    with open(output_markdown_file, "w", encoding="utf-8") as md_file:
        md_file.write(markdown_content)

    print(f"Markdown file created at {output_markdown_file}")


def main():
    # Change to Git root directory
    git_root = get_git_root()
    os.chdir(git_root)

    # Get project name from pyproject.toml
    project_name = get_project_name(git_root)
    if project_name is None:
        print(
            "Warning: Project name not found in pyproject.toml. Using directory name as fallback."
        )
        project_name = os.path.basename(git_root)

    # Create .clerk and .clerk/doc directories
    clerk_directory = os.path.join(git_root, ".clerk")
    clerk_doc_directory = os.path.join(clerk_directory, "docs")
    create_clerk_directory(clerk_directory)
    create_clerk_directory(clerk_doc_directory)

    # Generate tree with project name prefix
    gen_tree(git_root, os.path.join(clerk_directory, f"{project_name}_tree.txt"))

    # Run sphinx-build
    run_sphinx_build("docsrc", clerk_doc_directory)

    # Clean up .clerk/doc directory
    clean_directory_except_index_html(clerk_doc_directory)

    # Gather source code and convert documentation to Markdown with project name prefix
    gather_source_code("src", os.path.join(clerk_directory, f"{project_name}_src.md"))
    extract_div_convert_to_markdown(
        os.path.join(clerk_doc_directory, "index.html"),
        os.path.join(clerk_directory, f"{project_name}_docs.md"),
    )

    # Clean up temporary .clerk/docs directory
    shutil.rmtree(clerk_doc_directory)


if __name__ == "__main__":
    main()
