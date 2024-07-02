import os
from bs4 import BeautifulSoup
import markdownify
import subprocess
import shutil


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

    # Find and remove all <a> tags with class 'headerlink'
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
    # List to store file paths
    files = []

    # Walk through the directory and add file paths to the list
    for root, dirs, filenames in os.walk(src_directory):
        for filename in filenames:
            if filename.endswith(".py"):
                files.append(os.path.join(root, filename))

    # Sort the files to ensure __init__.py is at the beginning
    files.sort(key=lambda x: (not x.endswith("__init__.py"), x))

    # Open the output file
    with open(output_file, "w") as md_file:
        for file_path in files:
            # Write the file path as a header in the markdown file
            md_file.write(f"## {file_path}\n\n```py\n")

            # Open and read the content of the file
            with open(file_path, "r") as f:
                content = f.read()

            # Write the content to the markdown file
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
    # Read the HTML file
    with open(html_file_path, "r", encoding="utf-8") as file:
        html_content = file.read()

    # Parse the HTML content using BeautifulSoup
    #  soup = BeautifulSoup(html_content, "html.parser")

    cleaned_html_content = remove_header_links(html_content)
    soup = BeautifulSoup(cleaned_html_content, "html.parser")

    # Find the div with class 'document'
    document_div = soup.find("div", class_="document")

    # Convert the HTML of the document div to Markdown
    markdown_content = markdownify.markdownify(str(document_div), heading_style="ATX")

    # Write the Markdown content to the output file
    with open(output_markdown_file, "w", encoding="utf-8") as md_file:
        md_file.write(markdown_content)

    print(f"Markdown file created at {output_markdown_file}")



def main():
    # Change to Git root directory
    git_root = get_git_root()
    os.chdir(git_root)
    gen_tree(git_root, os.path.join(git_root, ".clerk/tree.txt"))

    # Create .clerk and .clerk/doc directories
    clerk_directory = os.path.join(git_root, ".clerk")
    clerk_doc_directory = os.path.join(clerk_directory, "docs")
    create_clerk_directory(clerk_directory)
    create_clerk_directory(clerk_doc_directory)

    # Run sphinx-build
    run_sphinx_build("docsrc", clerk_doc_directory)

    # Clean up .clerk/doc directory
    clean_directory_except_index_html(clerk_doc_directory)

    # Gather source code and convert documentation to Markdown
    gather_source_code("src", os.path.join(clerk_directory, "src.md"))
    extract_div_convert_to_markdown(
        os.path.join(clerk_doc_directory, "index.html"),
        os.path.join(clerk_doc_directory, "docs.md"),
    )

if __name__ == "__main__":
    main()
