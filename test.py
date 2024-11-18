#  import requests
import arxiv
from arxiv import Search
from arxiv import Client 
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

print(dir(arxiv))

def get_arxiv_data(url):
    """Extract arXiv ID from URL and fetch metadata."""
    paper_id = urlparse(url).path.split('/')[-1]
    search = Search(id_list=[paper_id])
    paper = next(search.results())
    
    return {
        'title': paper.title,
        'authors': [str(author) for author in paper.authors],
        'abstract': paper.summary,
        'published': paper.published,
        'url': url,
        'categories': paper.categories
    }

def format_rst(data):
    """Format paper data as RST."""
    rst = f"""
{data['title']}
{'=' * len(data['title'])}

:Author: {', '.join(data['authors'])}
:Published: {data['published'].strftime('%Y-%m-%d')}
:URL: {data['url']}
:Categories: {', '.join(data['categories'])}

Abstract
--------
{data['abstract']}

Keywords
--------
.. todo:: Extract or manually add keywords

Notes
-----
.. todo:: Add reading notes and key insights
"""
    return rst.strip()

def save_reference(url, output_dir='references'):
    """Fetch paper data and save as RST file."""
    data = get_arxiv_data(url)
    rst_content = format_rst(data)
    
    # Create output directory if needed
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Generate filename from title
    filename = data['title'].lower()
    filename = ''.join(c if c.isalnum() else '_' for c in filename)
    filename = filename[:50] + '.rst'  # Limit length
    
    filepath = Path(output_dir) / filename
    filepath.write_text(rst_content)
    
    return filepath

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) == 2:
        url = sys.argv[1]
    else:
        url = input("Please enter the arXiv URL: ").strip()
        
    if not url:
        print("No URL provided")
        sys.exit(1)
        
    try:
        filepath = save_reference(url)
        print(f"Reference saved to: {filepath}")
    except Exception as e:
        print(f"Error processing URL: {e}")
        sys.exit(1)
