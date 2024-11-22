"""
YouTube video utility - creates RST documentation with video metadata and embedded player
"""
from rich import print
import json
import subprocess
from pathlib import Path
from datetime import datetime
from slugify import slugify

def run_yt_command(video_id: str, option: str, output_file: Path = None) -> dict:
    """Run yt command and return parsed output or save to file."""
    url = f"https://youtu.be/{video_id}"
    cmd = ["yt", f"--{option}", url]
    
    try:
        if output_file:
            with open(output_file, 'w') as f:
                subprocess.run(cmd, stdout=f, text=True, check=True)
            return None
        else:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"[red]Error running yt command:[/red] {e}")
        print(f"stderr: {e.stderr}")
        raise
    except json.JSONDecodeError as e:
        print(f"[red]Error parsing yt output:[/red] {e}")
        raise


def create_include_files(video_dir: Path):
    """Create include files for notes and analysis."""
    includes = {
        "notes.rst": """\
notes
~~~~~

""",
        "analysis.rst": """\
analysis
~~~~~~~~

"""
    }
    
    for filename, content in includes.items():
        include_path = video_dir / filename
        include_path.write_text(content)
        print(f"Created include file: {include_path}")

def format_rst(data: dict) -> str:
    """Format video data as RST document."""
    rst = f"""\
{data['title']}
{'=' * len(data['title'])}

:Channel: {data['channel']}
:Published: {data['published_at'].strftime('%Y-%m-%d')}
:URL: {data['url']}
:Video ID: {data['id']}

.. youtube:: {data['id']}

:doc:`transcript`

:doc:`comments`

.. include:: notes.rst

.. include:: analysis.rst
"""
    return rst.strip()

def save_reference(video_id: str, output_dir: str = ".") -> Path:
    """Save video metadata as RST."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Create temporary dir with video ID until we get the title
    #  video_dir = output_path / video_id
    
    metadata = run_yt_command(video_id, "metadata")
    
    # Rename directory to use title
    video_dir = output_path / slugify(metadata["title"])
    video_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        transcript_path = video_dir / "transcript.rst"
        run_yt_command(video_id, "transcript", transcript_path)
        print(f"Saved transcript to: {transcript_path}")
    except:
        print("[yellow]Warning: Could not fetch transcript[/yellow]")
    
    try:
        comments_path = video_dir / "comments.rst"
        run_yt_command(video_id, "comments", comments_path)
        print(f"Saved comments to: {comments_path}")
    except:
        print("[yellow]Warning: Could not fetch comments[/yellow]")
    
    data = {
        "id": metadata["id"],
        "title": metadata["title"],
        "channel": metadata["channel"],
        "published_at": datetime.fromisoformat(metadata["published_at"].rstrip("Z")),
        "url": f"https://youtu.be/{video_id}"
    }
    
    create_include_files(video_dir)
    
    rst_content = format_rst(data)
    index_path = video_dir / "index.rst"
    index_path.write_text(rst_content)
    print(f"Created RST file: {index_path}")
    
    return index_path

def main():
    """Main entry point for command line usage."""
    import sys
    
    if len(sys.argv) == 2:
        video_id = sys.argv[1]
    else:
        video_id = input("Please enter the YouTube video ID: ").strip()
        
    if not video_id:
        print("[red]No video ID provided[/red]")
        sys.exit(1)
        
    try:
        index_path = save_reference(video_id)
        print("\n[green]✓ Successfully saved reference:[/green]")
        print(f"  RST: {index_path}")
    except Exception as e:
        print(f"[red]Error processing YouTube video:[/red] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
