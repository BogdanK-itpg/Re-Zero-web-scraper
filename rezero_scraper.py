import requests
from bs4 import BeautifulSoup
import re
import time
from urllib.parse import urlparse, urljoin
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Set
import logging

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
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
    chapter_type: str = "chapter"
    content: str = ""


@dataclass
class Phase:
    num: int
    title: str
    chapters: List[Chapter] = field(default_factory=list)


@dataclass
class Arc:
    num: int
    title: str
    phases: List[Phase] = field(default_factory=list)
    chapters: List[Chapter] = field(default_factory=list)


class WitchCultTranslating:
    TOC_URL = "https://witchculttranslation.com/table-of-content/"
    
    def __init__(self, delay: float = 1.5):
        self.session = requests.Session()
        self.session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        self.delay = delay
        self.seen_urls: Set[str] = set()
        self.seen_titles: Set[str] = set()
        self._arc_cache: List[Arc] = []
        self._chapter_list_cache: Dict[int, List[Chapter]] = {}
        self._logs: List[str] = []
    
    def _log(self, level: str, message: str):
        log_entry = f"{level} {message}"
        self._logs.append(log_entry)
        if level == "WARNING":
            logger.warning(message)
        elif level == "ERROR":
            logger.error(message)
        else:
            logger.info(message)
    
    def _fetch(self, url: str, retries: int = 3):
        for attempt in range(retries):
            try:
                time.sleep(self.delay)
                resp = self.session.get(url, timeout=30)
                resp.raise_for_status()
                return BeautifulSoup(resp.text, 'html.parser')
            except Exception as e:
                self._log("WARNING", f"Retry {attempt+1}/{retries} for {url}: {e}")
                time.sleep(self.delay * 2)
        self._log("ERROR", f"Failed to fetch after {retries} attempts: {url}")
        return None
    
    def _canonical(self, url: str) -> str:
        parsed = urlparse(url)
        return parsed._replace(query='', fragment='').geturl().rstrip('/')
    
    def _normalize_title(self, title: str) -> str:
        normalized = title.lower().strip()
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized
    
    def _mark_seen(self, url: str, title: str = "") -> bool:
        canon = self._canonical(url)
        if canon in self.seen_urls:
            return False
        self.seen_urls.add(canon)
        
        if title:
            norm_title = self._normalize_title(title)
            if norm_title in self.seen_titles:
                self._log("WARNING", f"Title duplicate detected: {title}")
                return False
            self.seen_titles.add(norm_title)
        
        return True
    
    def _detect_chapter_type(self, title: str) -> str:
        title_lower = title.lower()
        if 'prologue' in title_lower:
            return "prologue"
        elif 'interlude' in title_lower:
            return "interlude"
        elif 'epilogue' in title_lower:
            return "epilogue"
        elif 'side story' in title_lower:
            return "side_story"
        return "chapter"
    
    def _extract_chapter_num(self, title: str) -> Optional[int]:
        ch_match = re.search(r'chapter\s*(\d+)', title, re.I)
        if ch_match:
            return int(ch_match.group(1))
        return None
    
    def get_arc_urls(self) -> Dict[int, str]:
        soup = self._fetch(self.TOC_URL)
        if not soup:
            return {}
        
        arc_urls = {}
        content = soup.select_one('.entry-content')
        if not content:
            return {}
        
        for child in content.children:
            if not hasattr(child, 'get_text'):
                continue
            text = child.get_text(strip=True)
            if not child.name:
                continue
            
            arc_match = re.match(r'^Arc\s+(\d+)', text)
            if arc_match:
                arc_num = int(arc_match.group(1))
                link = child.find('a', href=True)
                if link and link.get('href'):
                    arc_urls[arc_num] = link.get('href')
        
        return arc_urls
    
    def _extract_chapters_from_arc_page(self, arc_num: int, arc_url: str) -> List[Chapter]:
        self._log("INFO", f"Extracting chapters from Arc {arc_num} page: {arc_url}")
        
        soup = self._fetch(arc_url)
        if not soup:
            self._log("ERROR", f"Failed to fetch Arc {arc_num} page")
            return []
        
        content = soup.select_one('.entry-content')
        if not content:
            self._log("WARNING", f"No entry-content found on Arc {arc_num} page")
            return []
        
        chapters = []
        current_phase = None
        
        for child in content.children:
            if not hasattr(child, 'get_text'):
                continue
            
            text = child.get_text(strip=True)
            if not child.name:
                continue
            
            if child.name in ('h1', 'h2', 'h3', 'h4'):
                phase_match = re.match(r'^Phase\s+(\d+)', text)
                if phase_match:
                    current_phase = int(phase_match.group(1))
                    continue
            
            if child.name not in ('ul', 'ol'):
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
                    href = urljoin(arc_url, href)
                if href.endswith('.pdf'):
                    continue
                
                check = title.lower()
                if 'chapter' not in check and 'prologue' not in check and 'interlude' not in check and 'epilogue' not in check:
                    continue
                
                if self._mark_seen(href, title):
                    ch_type = self._detect_chapter_type(title)
                    ch_num = self._extract_chapter_num(title)
                    
                    chapter = Chapter(
                        url=href,
                        title=title,
                        arc_num=arc_num,
                        arc_title=f"Arc {arc_num}",
                        phase_num=current_phase,
                        phase_title=f"Phase {current_phase}" if current_phase else None,
                        chapter_num=ch_num,
                        chapter_type=ch_type,
                        content=""
                    )
                    chapters.append(chapter)
                    self._log("INFO", f"  Added: {title} (type: {ch_type})")
        
        return chapters
    
    def get_toc(self) -> List[Arc]:
        if self._arc_cache:
            return self._arc_cache
            
        soup = self._fetch(self.TOC_URL)
        if not soup:
            self._log("ERROR", "Failed to fetch TOC")
            return []
        
        content = soup.select_one('.entry-content')
        if not content:
            self._log("ERROR", "No entry-content found on TOC page")
            return []
        
        arc_dict: Dict[int, Dict] = {}
        
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
                
                link = child.find('a', href=True)
                arc_url = link.get('href') if link else None
                
                arc_dict[arc_num] = {
                    'title': title_part,
                    'url': arc_url,
                    'chapters': [],
                    'phases': []
                }
                self._log("INFO", f"Arc {arc_num}: {title_part}")
                continue
            
            phase_match = re.match(r'^Phase\s+(\d+)', text)
            if phase_match:
                if arc_dict:
                    current_arc_num = max(arc_dict.keys())
                    if 'current_phase' not in arc_dict[current_arc_num]:
                        arc_dict[current_arc_num]['current_phase'] = int(phase_match.group(1))
                continue
            
            if child.name not in ('ul', 'ol'):
                continue
            
            if not arc_dict:
                continue
            
            current_arc_num = max(arc_dict.keys())
            
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
                
                ch_type = self._detect_chapter_type(title)
                ch_num = self._extract_chapter_num(title)
                
                if self._mark_seen(href, title):
                    phase_num = arc_dict[current_arc_num].get('current_phase')
                    chapter = Chapter(
                        url=href,
                        title=title,
                        arc_num=current_arc_num,
                        arc_title=arc_dict[current_arc_num]['title'],
                        phase_num=phase_num,
                        phase_title=f"Phase {phase_num}" if phase_num else None,
                        chapter_num=ch_num,
                        chapter_type=ch_type,
                        content=""
                    )
                    arc_dict[current_arc_num]['chapters'].append(chapter)
        
        for arc_num in arc_dict:
            arc_dict[arc_num].pop('current_phase', None)
        
        self._arc_cache = [
            Arc(
                num=n,
                title=v['title'],
                chapters=v['chapters']
            ) for n, v in sorted(arc_dict.items()) if v['chapters']
        ]
        
        return self._arc_cache
    
    def get_arcs(self) -> List[Arc]:
        return self.get_toc()
    
    def _is_metadata_block(self, text: str) -> bool:
        text_lower = text.lower().strip()
        metadata_keywords = [
            "posted on",
            "posted in",
            "by admin",
            "by author",
            "last updated",
            "published:",
            "categories:",
            "tags:",
        ]
        return any(kw in text_lower for kw in metadata_keywords)
    
    def _is_filler_block(self, text: str) -> bool:
        t = text.lower().strip()
        
        if not t:
            return True
        
        filler_patterns = [
            "translated by",
            "translation by",
            "snusertl",
            "support him on twitter",
            "support them on twitter",
            "all rights belong",
            "all rights reserved",
            "this is a translation",
            "web novel source",
            "patreon",
            "ko-fi",
            "twitter.com",
            "instagram",
            "posted on",
            "posted in",
            "by admin",
        ]
        
        for pattern in filler_patterns:
            if pattern in t:
                return True
        
        if t.startswith("http") and len(t) < 100:
            return True
        
        if all(c in "※ *-—·\u3000\t" for c in t):
            return True
        
        return False
    
    def _is_real_story(self, text: str) -> bool:
        t = text.strip()
        
        if len(t) < 40:
            return False
        
        if any(k in t.lower() for k in [
            "translated by", "posted on", "posted in", "by admin",
            "all rights", "web novel source", "patreon"
        ]):
            return False
        
        if "." in t or "—" in t or "!" in t or "?" in t:
            if any(c.isalpha() for c in t):
                return True
        
        return False
    
    def _extract_clean_content(self, container) -> tuple:
        VALID_TAGS = ["p", "h1", "h2", "h3", "blockquote"]
        
        all_elements = container.find_all(VALID_TAGS, recursive=True)
        
        raw_p_count = len([el for el in all_elements if el.name == "p"])
        
        cleaned_elements = []
        started = False
        removed_filler = 0
        titles_seen = set()
        
        for el in all_elements:
            text = el.get_text(strip=True)
            
            if not text:
                continue
            
            if self._is_metadata_block(text):
                removed_filler += 1
                continue
            
            if not started:
                if self._is_filler_block(text):
                    removed_filler += 1
                    continue
                
                if not self._is_real_story(text):
                    removed_filler += 1
                    continue
                
                started = True
            
            if el.name in ('h1', 'h2', 'h3'):
                norm_title = self._normalize_title(text)
                if norm_title in titles_seen:
                    removed_filler += 1
                    continue
                titles_seen.add(norm_title)
            
            cleaned_elements.append(text)
        
        final_paragraphs = len(cleaned_elements)

        if final_paragraphs > 0:
            content_with_split = []
            dialogue_split_count = 0
            for para in cleaned_elements:
                if "―" in para:
                    content_with_split.extend(self._split_dialogue_paragraphs(para))
                    dialogue_split_count += 1
                else:
                    content_with_split.append(para)
            
            content = '\n'.join(content_with_split)
            final_paragraphs = len(content_with_split)
            
            self._log("INFO", f"<p> tags found: {raw_p_count}")
            self._log("INFO", f"Output paragraphs: {final_paragraphs}")
            if dialogue_split_count > 0:
                self._log("FIX", f"Dialogue split applied to {dialogue_split_count} paragraphs")
            
            if final_paragraphs < raw_p_count:
                self._log("WARNING", f"Paragraph count decreased - possible merging detected")
            else:
                self._log("OK", "No paragraph merging detected")
        else:
            content = '\n'.join(cleaned_elements)
        self._log("DEBUG", f"Removed filler/metadata: {removed_filler}")
        
        if cleaned_elements:
            self._log("DEBUG", f"First paragraph: {cleaned_elements[0][:60]}...")

        if final_paragraphs < 3:
            self._log("WARNING", f"Low paragraph count ({final_paragraphs}), content may be broken")

        return content, final_paragraphs
    
    def scrape_chapter(self, chapter: Chapter) -> str:
        if chapter.url.endswith('.pdf'):
            return f"[PDF - {chapter.url}]"
        
        soup = self._fetch(chapter.url)
        if not soup:
            self._log("ERROR", f"Failed to fetch chapter: {chapter.title}")
            return ""
        
        container = None
        for selector in ['article', '.entry-content', '.post-content', '.content', 'main']:
            candidate = soup.select_one(selector)
            if candidate:
                container = candidate
                break
        
        if not container:
            self._log("WARNING", f"No content container found for: {chapter.title}")
            return ""
        
        for bad in container.select('.sharedaddy, .related-posts, .author-bio, .comments, .comment, script, style, iframe, nav, footer, .sidebar, .ad, .ads, .social, .share, .entry-meta, .post-meta, .tags, .categories, .post-date, .post-author'):
            bad.decompose()
        
        content, para_count = self._extract_clean_content(container)
        
        if not content or len(content) < 100:
            self._log("WARNING", f"Content too short for {chapter.title}, trying fallback")
            paragraphs = []
            for p in container.find_all('p', recursive=True):
                text = p.get_text(strip=True)
                if text and len(text) > 20:
                    paragraphs.append(text)
            if paragraphs:
                content = '\n'.join(paragraphs)
                self._log("INFO", f"Fallback extracted {len(paragraphs)} paragraphs")
        
        first_line = content.split('\n')[0] if content else ""
        
        if first_line and self._is_filler_block(first_line):
            self._log("ERROR", f"Filler still present in first paragraph: {first_line[:50]}")
        
        if len(content) > 100:
            self._log("INFO", f"Content extracted: {chapter.title} ({len(content)} chars, {para_count} paragraphs)")
            return content
        
        self._log("WARNING", f"Content too short for {chapter.title}: {len(content)} chars")
        return content if content else ""
    
    def _verify_order(self, arc_num: int, chapters: List[Chapter]) -> List[Chapter]:
        self._log("INFO", f"Verifying order for Arc {arc_num}...")
        
        arc_url = None
        for arc in self._arc_cache:
            if arc.num == arc_num:
                break
        
        arc_urls = self.get_arc_urls()
        if arc_num in arc_urls:
            expected_chapters = self._extract_chapters_from_arc_page(arc_num, arc_urls[arc_num])
            
            expected_titles = [self._normalize_title(c.title) for c in expected_chapters]
            found_titles = [self._normalize_title(c.title) for c in chapters]
            
            missing = []
            for i, expected in enumerate(expected_titles):
                if expected not in found_titles:
                    missing.append(expected_chapters[i].title)
            
            if missing:
                self._log("WARNING", f"Arc {arc_num} - Missing chapters: {missing}")
                for m in missing:
                    for ec in expected_chapters:
                        if self._normalize_title(ec.title) == m:
                            chapters.append(ec)
                            self._log("FIX", f"Inserted missing: {m}")
                            break
            
            duplicates = []
            seen = set()
            for c in chapters:
                norm = self._normalize_title(c.title)
                if norm in seen:
                    duplicates.append(c.title)
                seen.add(norm)
            
            if duplicates:
                self._log("WARNING", f"Arc {arc_num} - Duplicates found: {duplicates}")
                seen = set()
                chapters = [c for c in chapters if self._normalize_title(c.title) not in seen or not seen.add(self._normalize_title(c.title))]
                self._log("FIX", f"Removed {len(duplicates)} duplicates")
        
        return chapters
    
    def scrape_arc(self, arc_num: int) -> List[Chapter]:
        arcs = self.get_toc()
        arc = next((a for a in arcs if a.num == arc_num), None)
        if not arc:
            self._log("ERROR", f"Arc {arc_num} not found")
            return []
        
        self._log("INFO", f"Scraping Arc {arc_num}: {arc.title}")
        chapters = list(arc.chapters)
        
        if not chapters:
            arc_urls = self.get_arc_urls()
            if arc_num in arc_urls:
                chapters = self._extract_chapters_from_arc_page(arc_num, arc_urls[arc_num])
        
        for i, ch in enumerate(chapters):
            self._log("INFO", f"  {i+1}/{len(chapters)}: {ch.title}")
            ch.content = self.scrape_chapter(ch)
        
        chapters = [c for c in chapters if c.content]
        
        chapters = self._verify_order(arc_num, chapters)
        
        self._log("INFO", f"Arc {arc_num} complete: {len(chapters)} chapters")
        return chapters
    
    def scrape_range(self, start_arc: int, end_arc: int) -> List[Chapter]:
        all_chapters = []
        for arc_num in range(start_arc, end_arc + 1):
            self._log("INFO", f"Processing Arc {arc_num}...")
            chapters = self.scrape_arc(arc_num)
            all_chapters.extend(chapters)
        return all_chapters
    
    def scrape_all(self) -> List[Chapter]:
        arcs = self.get_toc()
        all_chapters = []
        for arc in arcs:
            self._log("INFO", f"Processing Arc {arc.num}...")
            chapters = self.scrape_arc(arc.num)
            all_chapters.extend(chapters)
        return all_chapters
    
    def get_latest(self) -> List[Chapter]:
        arcs = self.get_toc()
        if not arcs:
            self._log("ERROR", "No arcs found")
            return []
        latest_arc = arcs[-1]
        self._log("INFO", f"Getting latest from Arc {latest_arc.num}")
        return self.scrape_arc(latest_arc.num)
    
    def _split_dialogue_paragraphs(self, text: str) -> List[str]:
        if "―" not in text:
            return [text]
        
        parts = re.split(r'(?=―)', text)
        
        cleaned = []
        for p in parts:
            stripped = p.strip()
            if stripped:
                cleaned.append(stripped)
        
        return cleaned
    
    def _apply_dialogue_split(self, content: str) -> str:
        lines = content.split('\n')
        
        all_paragraphs = []
        for para in lines:
            if "―" in para:
                split_paras = self._split_dialogue_paragraphs(para)
                all_paragraphs.extend(split_paras)
            else:
                if para.strip():
                    all_paragraphs.append(para.strip())
        
        return '\n'.join(all_paragraphs)

    def get_logs(self) -> List[str]:
        return self._logs