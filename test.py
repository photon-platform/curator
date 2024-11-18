from rich import print
import arxiv
from pathlib import Path
from urllib.parse import urlparse
from slugify import slugify

client = arxiv.Client()

#  'authors',
#  'categories',
#  'comment',
#  'doi',
#  'download_pdf',
#  'download_source',
#  'entry_id',
#  'get_short_id',
#  'journal_ref',
#  'links',
#  'pdf_url',
#  'primary_category',
#  'published',
#  'summary',
#  'title',
#  'updated'

def get_arxiv_data(url):
    """Extract arXiv ID from URL and fetch metadata."""
    paper_id = urlparse(url).path.split('/')[-1]
    search = arxiv.Search(id_list=[paper_id])
    print(dir(search))
    results = client.results(search)
    print(dir(results))
    paper = next(results)
    print(dir(paper))
    print(paper)
    
    return {
        'title': paper.title,
        'authors': [str(author) for author in paper.authors],
        'abstract': paper.summary,
        'published': paper.published,
        'url': url,
        'categories': paper.categories,
        'paper_id': paper_id,
        'paper': paper
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
:PDF: {data['paper_id']}.pdf

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

    paper_dir = Path(output_dir) / slugify(data['title'])
    paper_dir.mkdir(parents=True, exist_ok=True)
    
    index_path = paper_dir / 'index.rst'
    index_path.write_text(rst_content)
    
    pdf_path = paper_dir / f"{data['paper_id']}.pdf"
    print(pdf_path)
    print()
    data['paper'].download_pdf(str(paper_dir))
    
    return index_path, pdf_path

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
        rst_path, pdf_path = save_reference(url)
        print(f"Reference saved to: {rst_path}")
        print(f"PDF saved to: {pdf_path}")
    except Exception as e:
        print(f"Error processing URL: {e}")
        sys.exit(1)
