import requests
from bs4 import BeautifulSoup
import re
import time
from urllib.parse import urlparse
from dataclasses import dataclass, field
from typing import Optional, List
import logging

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


@dataclass
class Chapter:
    url: str
    title: str
    arc_num: int
    arc_title: str
    phase_num: Optional[int] = None
    phase_title: Optional[str] = None
    chapter_num: Optional[int] = None
    content: str = ""


@dataclass  
class Arc:
    num: int
    title: str
    phases: list = field(default_factory=list)


class WitchCultTranslating:
    TOC_URL = "https://witchculttranslation.com/table-of-content/"
    
    def __init__(self, delay: float = 1.5):
        self.session = requests.Session()
        self.session.headers['User-Agent'] = 'Mozilla/5.0'
        self.delay = delay
        self.seen_urls = set()
        self._arc_cache = []
    
    def _fetch(self, url: str, retries: int = 3):
        for attempt in range(retries):
            try:
                time.sleep(self.delay)
                resp = self.session.get(url, timeout=30)
                resp.raise_for_status()
                return BeautifulSoup(resp.text, 'html.parser')
            except Exception:
                time.sleep(self.delay * 2)
        return None
    
    def _canonical(self, url: str) -> str:
        return urlparse(url)._replace(query='', fragment='').geturl()
    
    def _mark_seen(self, url: str) -> bool:
        canon = self._canonical(url)
        if canon in self.seen_urls:
            return False
        self.seen_urls.add(canon)
        return True
    
    def get_toc(self) -> List[Arc]:
        if self._arc_cache:
            return self._arc_cache
            
        soup = self._fetch(self.TOC_URL)
        if not soup:
            return []
        
        content = soup.select_one('.entry-content')
        if not content:
            return []
        
        arc_dict = {}
        current_arc = (0, "")
        current_phase = None
        
        for child in content.children:
            if not hasattr(child, 'get_text'):
                continue
            
            text = child.get_text(strip=True)
            
            if not child.name:
                continue
            
            arc_match = re.match(r'^Arc\s+(\d+)', text)
            if arc_match:
                arc_num = int(arc_match.group(1))
                title_part = re.sub(r'^Arc\s+\d+\s*[-–]\s*', '', text)
                title_part = re.sub(r'\s*[\u0080-\uFFFF].*$', '', title_part).strip()
                if not title_part:
                    title_part = f"Arc {arc_num}"
                current_arc = (arc_num, title_part)
                current_phase = None
                arc_dict[arc_num] = {'title': title_part, 'chapters': [], 'phase': None}
                continue
            
            phase_match = re.match(r'^Phase\s+(\d+)', text)
            if phase_match:
                current_phase = int(phase_match.group(1))
                continue
            
            if child.name not in ('ul', 'ol'):
                continue
            
            if current_arc[0] == 0:
                continue
            
            for li in child.find_all('li', recursive=False):
                link = li.find('a', href=True)
                if not link:
                    continue
                    
                href = link.get('href', '')
                title = link.get_text(strip=True)
                
                if not href or not title:
                    continue
                if not href.startswith('http'):
                    continue
                if href.endswith('.pdf'):
                    continue
                
                check = title.lower()
                if 'chapter' not in check and 'prologue' not in check and 'interlude' not in check:
                    continue
                
                ch_match = re.search(r'chapter\s*(\d+)', title, re.I)
                ch_num = int(ch_match.group(1)) if ch_match else None
                
                if self._mark_seen(href):
                    if current_arc[0] not in arc_dict:
                        arc_dict[current_arc[0]] = {'title': current_arc[1], 'chapters': [], 'phase': None}
                    arc_dict[current_arc[0]]['chapters'].append(Chapter(
                        url=href,
                        title=title,
                        arc_num=current_arc[0],
                        arc_title=current_arc[1],
                        phase_num=current_phase,
                        phase_title=f"Phase {current_phase}" if current_phase else None,
                        chapter_num=ch_num,
                        content=""
                    ))
        
        self._arc_cache = [Arc(num=n, title=v['title'], phases=v['chapters']) 
                       for n, v in sorted(arc_dict.items()) if v['chapters']]
        return self._arc_cache
    
    def get_arcs(self) -> List[Arc]:
        return self.get_toc()
    
    def scrape_chapter(self, chapter: Chapter) -> str:
        if chapter.url.endswith('.pdf'):
            return "[PDF - " + chapter.url + "]"
        
        soup = self._fetch(chapter.url)
        if not soup:
            return ""
        
        containers = soup.select('article .entry-content, .entry-content, .post-content')
        
        for container in containers:
            for bad in container.select('.sharedaddy, .related-posts, .author-bio, .comments, script, style, iframe'):
                bad.decompose()
            
            text = container.get_text(separator='\n', strip=True)
            if len(text) > 300:
                return text
        
        return ""
    
    def scrape_arc(self, arc_num: int) -> List[Chapter]:
        arcs = self.get_toc()
        arc = next((a for a in arcs if a.num == arc_num), None)
        if not arc:
            logger.error("Arc " + str(arc_num) + " not found")
            return []
        
        print("Scraping Arc " + str(arc_num))
        chapters = arc.phases
        
        for i, ch in enumerate(chapters):
            print(f"  {i+1}/{len(chapters)}: {ch.title}")
            ch.content = self.scrape_chapter(ch)
        
        return [c for c in chapters if c.content]
    
    def scrape_range(self, start_arc: int, end_arc: int) -> List[Chapter]:
        all_chapters = []
        for arc_num in range(start_arc, end_arc + 1):
            chapters = self.scrape_arc(arc_num)
            all_chapters.extend(chapters)
        return all_chapters
    
    def scrape_all(self) -> List[Chapter]:
        arcs = self.get_toc()
        all_chapters = []
        for arc in arcs:
            chapters = self.scrape_arc(arc.num)
            all_chapters.extend(chapters)
        return all_chapters
    
    def get_latest(self) -> List[Chapter]:
        arcs = self.get_toc()
        if not arcs:
            return []
        latest_arc = arcs[-1]
        return self.scrape_arc(latest_arc.num)