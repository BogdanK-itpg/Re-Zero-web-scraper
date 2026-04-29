import argparse
import sys
import os
from datetime import datetime
from ebooklib import epub

from rezero_scraper import WitchCultTranslating, Chapter


def create_epub(chapters, output_path, title):
    book = epub.EpubBook()
    book.set_identifier(f'rezero_{int(datetime.now().timestamp())}')
    book.set_title(title)
    book.set_language('en')
    book.add_author('Tappei Nagatsuki')
    
    book.toc = []
    spine = ['nav']
    current_arc = None
    current_phase = None
    
    sorted_chapters = sorted(chapters, key=lambda c: (
        c.arc_num,
        c.phase_num or 0,
        c.chapter_num or 0
    ))
    
    for ch in sorted_chapters:
        if ch.arc_num != current_arc:
            current_arc = ch.arc_num
            current_phase = None
            arc_link = epub.Link(f'arc_{current_arc}.xhtml', f'Arc {current_arc}: {ch.arc_title}', f'arc_{current_arc}')
            book.toc.append(arc_link)
        
        if ch.phase_num and ch.phase_num != current_phase:
            current_phase = ch.phase_num
            phase_link = epub.Link(f'phase_{current_arc}_{current_phase}.xhtml', f'Phase {current_phase}', f'phase_{current_arc}_{current_phase}')
            book.toc.append(phase_link)
        
        file_name = f'chapter_{ch.arc_num}_{ch.chapter_num or "x"}.xhtml'
        html_content = f'''<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{ch.title}</title>
</head>
<body>
    <h1>{ch.title}</h1>
    <p>Arc {ch.arc_num}: {ch.arc_title}</p>
    {f"<p>Phase {ch.phase_num}: {ch.phase_title}</p>" if ch.phase_num else ""}
    <hr/>
    <div>
{chr(10).join(ch.content.split(chr(10)))}
    </div>
</body>
</html>'''
        
        c1 = epub.EpubHtml(file_name, ch.title, file_name)
        c1.content = html_content
        book.add_item(c1)
        spine.append(c1)
    
    book.spine = spine
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    
    try:
        epub.write_epub(output_path, book, {})


        return True
    except Exception as e:
        print(f"Error writing EPUB: {e}")
        return False


def scrape_to_epub(chapters, output, custom_title=None):
    if not chapters:
        print("No chapters to export!")
        return False
    
    title = custom_title or "Re:Zero Web Novel"
    output_path = output or f"ReZero_{datetime.now().strftime('%Y%m%d')}.epub"
    
    print(f"Creating EPUB with {len(chapters)} chapters...")
    if create_epub(chapters, output_path, title):
        print(f"EPUB saved to: {output_path}")
        return True
    return False


def main():
    parser = argparse.ArgumentParser(description='Re:Zero Scraper - EPUB Generator')
    parser.add_argument('--all', action='store_true', help='Scrape all arcs')
    parser.add_argument('--arc', type=int, help='Scrape single arc (e.g., --arc 7)')
    parser.add_argument('--range', nargs=2, type=int, metavar=('START', 'END'), help='Scrape arc range (e.g., --range 5 8)')
    parser.add_argument('--chapter', nargs=2, type=int, metavar=('ARC', 'NUM'), help='Scrape specific chapter (e.g., --chapter 6 23)')
    parser.add_argument('--latest', action='store_true', help='Scrape latest chapter only')
    parser.add_argument('--output', type=str, help='Output filename')
    parser.add_argument('--title', type=str, help='EPUB title')
    parser.add_argument('--delay', type=float, default=1.5, help='Delay between requests (seconds)')
    
    args = parser.parse_args()
    
    if not any([args.all, args.arc, args.range, args.chapter, args.latest]):
        parser.print_help()
        return
    
    scraper = WitchCultTranslating(delay=args.delay)
    
    try:
        if args.all:
            print("Scraping all arcs...")
            chapters = scraper.scrape_all()
        elif args.arc:
            print(f"Scraping Arc {args.arc}...")
            chapters = scraper.scrape_arc(args.arc)
        elif args.range:
            start, end = args.range
            print(f"Scraping Arc {start} to {end}...")
            chapters = scraper.scrape_range(start, end)
        elif args.chapter:
            arc_num, ch_num = args.chapter
            print(f"Scraping Arc {arc_num} Chapter {ch_num}...")
            chapters = scraper.scrape_arc(arc_num)
            chapters = [c for c in chapters if c.chapter_num == ch_num]
        elif args.latest:
            print("Scraping latest content...")
            chapters = scraper.get_latest()
            if chapters:
                chapters = [chapters[-1]]
        
        if chapters:
            scrape_to_epub(chapters, args.output, args.title)
        else:
            print("No chapters found!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()