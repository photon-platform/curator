"""
ArXiv reference utility - downloads papers and creates RST documentation
"""
from rich import print
import arxiv
from pathlib import Path
from slugify import slugify

client = arxiv.Client()

def get_paper_data(paper_id: str) -> dict:
    """Fetch paper metadata from arXiv."""
    search = arxiv.Search(id_list=[paper_id])
    paper = next(client.results(search))
    
    return {
        'title': paper.title,
        'authors': [str(author) for author in paper.authors],
        'abstract': paper.summary,
        'published': paper.published,
        'categories': paper.categories,
        'comment': paper.comment,
        'doi': paper.doi,
        'journal_ref': paper.journal_ref,
        'primary_category': paper.primary_category,
        'paper_id': paper_id,
        'paper': paper
    }

def format_rst(data: dict) -> str:
    """Format paper data as RST document."""
    # Create slug from title
    slug = slugify(data['title'])
    
    rst = f""".. _{slug}:

{data['title']}
{'=' * len(data['title'])}

:Authors: {', '.join(data['authors'])}
:Published: {data['published'].strftime('%Y-%m-%d')}
:arXiv: https://arxiv.org/abs/{data['paper_id']}
:PDF: {data['paper_id']}.pdf
:DOI: {data['doi'] or 'N/A'}
:Journal Reference: {data['journal_ref'] or 'N/A'}
:Primary Category: {data['primary_category']}
:Categories: {', '.join(data['categories'])}
:Comment: {data['comment'] or 'N/A'}

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

def save_reference(paper_id: str, output_dir: str = 'references') -> tuple[Path, Path]:
    """Save paper metadata as RST and download PDF."""
    data = get_paper_data(paper_id)
    rst_content = format_rst(data)

    # Create paper directory using slugified title
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    paper_dir = output_path / slugify(data['title'])
    paper_dir.mkdir(parents=True, exist_ok=True)
    
    # Save index.rst
    index_path = paper_dir / 'index.rst'
    index_path.write_text(rst_content)
    print(f"Created RST file: {index_path}")
    
    # Download PDF
    pdf_path = data['paper'].download_pdf(str(paper_dir))
    print(f"Downloaded PDF: {pdf_path}")
    
    return index_path, pdf_path

def main():
    """Main entry point for command line usage."""
    import sys
    
    if len(sys.argv) == 2:
        paper_id = sys.argv[1]
    else:
        paper_id = input("Please enter the arXiv ID (e.g. 2208.04202): ").strip()
        
    if not paper_id:
        print("No arXiv ID provided")
        sys.exit(1)
        
    try:
        index_path, pdf_path = save_reference(paper_id)
        print("\n[green]✓ Successfully saved reference:[/green]")
        print(f"  RST: {index_path}")
        print(f"  PDF: {pdf_path}")
    except Exception as e:
        print(f"[red]Error processing arXiv ID:[/red] {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
