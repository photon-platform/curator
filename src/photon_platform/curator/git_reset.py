import os
import subprocess
import shutil
import sys

def get_remote_origin_url(repo_path):
    """
    Gets the URL of the 'origin' remote for the Git repository.

    Args:
        repo_path (str): The path to the Git repository.

    Returns:
        str or None: The URL of the 'origin' remote, or None if not found or an error occurs.
    """
    remote_url = None
    try:
        # Get remote origin URL
        result_url = subprocess.run(
            ['git', 'config', '--get', 'remote.origin.url'],
            cwd=repo_path, capture_output=True, text=True, check=False # check=False to handle no remote gracefully
        )
        if result_url.returncode == 0 and result_url.stdout.strip():
            remote_url = result_url.stdout.strip()
        else:
             # This is not an error, just means no remote is configured
             print("Info: No remote 'origin' URL found or configured.", file=sys.stderr)

    except FileNotFoundError:
        print("Error: 'git' command not found. Make sure Git is installed and in your PATH.", file=sys.stderr)
        return None
    except subprocess.CalledProcessError as e: # Should not happen with check=False, but for safety
         print(f"Error getting remote URL: {e.stderr}", file=sys.stderr)
         return None
    except Exception as e:
        print(f"An unexpected error occurred while getting remote URL: {e}", file=sys.stderr)
        return None

    return remote_url


def reset_git_repo(repo_path='.', force_push=False):
    """
    Resets the Git repository at the specified path to a 'main' branch
    and optionally force pushes.

    This involves:
    1. Finding the remote origin URL.
    2. Asking for confirmation.
    3. Deleting the .git directory.
    4. Re-initializing the repository with the 'main' branch.
    5. Adding the remote origin back (if found).
    6. Staging all files.
    7. Creating an initial commit.
    8. Optionally force-pushing to the 'main' branch on remote origin.

    Args:
        repo_path (str): The path to the Git repository (default: current directory).
        force_push (bool): Whether to force push to remote 'main' branch after reset (default: False).
    """
    git_dir = os.path.join(repo_path, '.git')
    target_branch_name = 'main' # Hardcode the target branch name

    # Check if the .git directory exists
    if not os.path.isdir(git_dir):
        print(f"Error: No Git repository found at '{os.path.abspath(repo_path)}'.", file=sys.stderr)
        return

    print(f"Found Git repository at: {os.path.abspath(repo_path)}")

    # --- Step 1: Get the remote origin URL ---
    remote_url = get_remote_origin_url(repo_path)
    if remote_url:
        print(f"Found remote 'origin' URL: {remote_url}")

    # --- Step 2: Ask for confirmation ---
    print("\n!!! WARNING !!!")
    print("This script will permanently delete the existing Git history (.git directory)")
    print(f"and create a fresh repository with the branch '{target_branch_name}'.")
    if force_push and remote_url:
         print(f"It will also FORCE PUSH the new history to '{remote_url}' on branch '{target_branch_name}', overwriting remote history.")
    print("This action cannot be undone.")

    confirm = input(f"Are you absolutely sure you want to reset the Git repository at '{os.path.abspath(repo_path)}'? (y/N): ")

    if confirm.lower() != 'y':
        print("Operation cancelled by user.")
        return

    # --- Step 3: Delete the .git directory ---
    try:
        print(f"\nDeleting existing .git directory: {git_dir}...")
        shutil.rmtree(git_dir)
        print(".git directory deleted successfully.")
    except OSError as e:
        print(f"Error deleting .git directory: {e}", file=sys.stderr)
        return
    except Exception as e:
        print(f"An unexpected error occurred during deletion: {e}", file=sys.stderr)
        return

    # --- Step 4: Re-initialize the repository with 'main' branch ---
    try:
        print(f"Initializing new Git repository with branch '{target_branch_name}'...")
        # Use --initial-branch to set the desired branch name (Git 2.28+)
        init_cmd = ['git', 'init', f'--initial-branch={target_branch_name}']
        init_result = subprocess.run(init_cmd, cwd=repo_path, check=False, capture_output=True, text=True)

        if init_result.returncode != 0:
             # If --initial-branch failed (maybe older Git version?), try plain 'git init'
             # Git might create 'master' by default, but we'll proceed assuming 'main' is the goal.
             # Subsequent steps like push will target 'main'. If the actual branch differs, push might fail later.
             print(f"Warning: Setting initial branch to '{target_branch_name}' failed (maybe older Git version?). Retrying with default 'git init'...")
             print("         The script will still attempt to push to 'main' if force push is enabled.")
             init_cmd = ['git', 'init']
             init_result = subprocess.run(init_cmd, cwd=repo_path, check=True, capture_output=True, text=True)

        print(f"New Git repository initialized. Intended branch: '{target_branch_name}'.")

    except FileNotFoundError:
         print("Error: 'git' command not found. Make sure Git is installed and in your PATH.", file=sys.stderr)
         return # Cannot proceed without git
    except subprocess.CalledProcessError as e:
        print(f"Error initializing Git repository: {e.stderr}", file=sys.stderr)
        return
    except Exception as e:
        print(f"An unexpected error occurred during git init: {e}", file=sys.stderr)
        return


    # --- Step 5: Add the remote origin back (if found) ---
    if remote_url:
        try:
            print(f"Adding remote 'origin' back: {remote_url}...")
            subprocess.run(['git', 'remote', 'add', 'origin', remote_url], cwd=repo_path, check=True, capture_output=True)
            print("Remote 'origin' added successfully.")
        except subprocess.CalledProcessError as e:
            # Check if the error is "remote origin already exists" - might happen if init created it somehow
            if "remote origin already exists" in e.stderr.decode():
                print("Info: Remote 'origin' already exists, skipping add.")
            else:
                print(f"Error adding remote 'origin': {e.stderr.decode()}", file=sys.stderr)
                # If remote add fails, we definitely can't push
                force_push = False
                print("Disabling force push due to error adding remote.", file=sys.stderr)
        except Exception as e:
            print(f"An unexpected error occurred while adding remote: {e}", file=sys.stderr)
            force_push = False
            print("Disabling force push due to unexpected error.", file=sys.stderr)


    # --- Step 6: Stage all files ---
    try:
        print("Staging all files...")
        subprocess.run(['git', 'add', '.'], cwd=repo_path, check=True, capture_output=True)
        print("All files staged.")
    except subprocess.CalledProcessError as e:
        print(f"Error staging files: {e.stderr.decode()}", file=sys.stderr)
        print("Aborting commit and push due to staging errors.", file=sys.stderr)
        return
    except Exception as e:
        print(f"An unexpected error occurred during git add: {e}", file=sys.stderr)
        return


    # --- Step 7: Create an initial commit ---
    try:
        print("Creating initial commit...")
        commit_message = "Initial commit after reset"
        subprocess.run(['git', 'commit', '-m', commit_message], cwd=repo_path, check=True, capture_output=True)
        print(f"Initial commit created with message: '{commit_message}'")
    except subprocess.CalledProcessError as e:
        stderr_output = e.stderr.decode()
        print(f"Error creating initial commit: {stderr_output}", file=sys.stderr)
        # Check if the error is because the branch name is different from 'main' (e.g., 'master' on older git)
        if "master" in stderr_output and target_branch_name == "main":
             print("Hint: The initial branch might be 'master' due to older Git version. The script targeted 'main'.", file=sys.stderr)
        elif "nothing to commit" in stderr_output:
             print("Info: No changes detected to commit.")
             # Allow push attempt even if nothing to commit initially, user might want to push empty branch
        else:
            # If commit fails for other reasons, don't push
            print("Aborting push due to commit error.", file=sys.stderr)
            force_push = False # Ensure we don't try to push
    except Exception as e:
        print(f"An unexpected error occurred during git commit: {e}", file=sys.stderr)
        return


    # --- Step 8: Force push to remote 'main' branch (if requested and possible) ---
    if force_push:
        if remote_url:
            try:
                print(f"\nAttempting to force push to origin branch '{target_branch_name}'...")
                push_cmd = ['git', 'push', '--force', 'origin', target_branch_name]
                subprocess.run(push_cmd, cwd=repo_path, check=True, capture_output=True, text=True)
                print(f"Successfully force pushed to origin/{target_branch_name}.")
            except subprocess.CalledProcessError as e:
                print(f"Error during force push: {e.stderr}", file=sys.stderr)
                print("Please check the remote repository status, branch name ('main'), and your permissions.")
            except Exception as e:
                print(f"An unexpected error occurred during force push: {e}", file=sys.stderr)
        else:
             print("\nSkipping force push: Remote 'origin' URL was not found or could not be added.", file=sys.stderr)


    print("\nGit repository reset process finished.")
    print("Current status:")
    try:
        # Show status after all operations
        subprocess.run(['git', 'status'], cwd=repo_path, check=True, text=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
         print(f"Could not run 'git status': {e}", file=sys.stderr)


def main():
    """
    CLI entry point for `git‑reset`.  Parses arguments and
    calls `reset_git_repo`.
    """
    target_repo_path = '.'
    do_force_push = False

    # recognise --force / -f
    if '--force' in sys.argv or '-f' in sys.argv:
        do_force_push = True
        sys.argv[:] = [arg for arg in sys.argv if arg not in ('--force', '-f')]

    # remaining positional argument → repo path
    if len(sys.argv) > 1:
        target_repo_path = sys.argv[1]

    reset_git_repo(target_repo_path, force_push=do_force_push)


if __name__ == "__main__":
    main()

