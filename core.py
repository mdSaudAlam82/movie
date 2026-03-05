"""
HubLoader Core v2 — All bypass logic.
FIXED:
  1. gamerxyt.com added to bypass chain (hubcloud.foo -> gamerxyt.com)
  2. hblinks.dad: prefer hubdrive.space over hubcloud.foo
  3. Search: try multiple hdhub4u mirrors
  4. Episode detection: wider keyword net
  5. Card parsing: handle both figcaption and article structures
  6. hubcloud.foo /drive/ var url pattern handled
"""

import requests
from bs4 import BeautifulSoup
import re, base64, json, time, urllib.parse

# ── Stealth Headers (unchanged from hunter2.py) ──────────────────────────────
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
              'image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
}

# FIX: gamerxyt.com added — final hop after hubcloud.foo
BYPASS_DOMS = ['gadgetsweb', 'cryptoinsights', 'hubdrive', 'hubcloud',
               'hubcdn', 'hblinks', 'gamerxyt']

HDHUB_DOMAINS = [
    'https://new4.hdhub4u.fo',
    'https://hdhub4u.fo',
    'https://hdhub4u.tv',
    'https://hdhub4u.gd',
]

# ── Session Factory ───────────────────────────────────────────────────────────
def make_session():
    s = requests.Session()
    s.cookies.set('xyt', '1', domain='hubdrive.space')
    return s


# ── BYPASS FUNCTIONS (unchanged core logic + fixes) ───────────────────────────
def rot13(s):
    return "".join(
        chr((ord(c) - 65 + 13) % 26 + 65) if 'A' <= c <= 'Z'
        else chr((ord(c) - 97 + 13) % 26 + 97) if 'a' <= c <= 'z'
        else c for c in s
    )


def extract_real_video_link(html_text, response_url):
    if "googleusercontent.com" in response_url or "drive.google.com" in response_url:
        if "lh3." not in response_url and "/profile/" not in response_url:
            return response_url
    m = re.search(r'(https?://video-downloads\.googleusercontent\.com/[^\s\'"><\\]+)', html_text)
    if m: return m.group(1)
    for link in re.findall(r'(https?://[a-zA-Z0-9-]*googleusercontent\.com/[^\s\'"><\\]+)', html_text):
        if "lh3." not in link and "/profile/" not in link and "/photo/" not in link:
            return link
    m = re.search(r'(https?://[^\s\'"><\\]+\.(?:mkv|mp4|zip|rar|7z)[^\s\'"><\\]*)', html_text)
    if m: return m.group(1)
    return None


def process_redirect_server(session, url, server_name="Server"):
    h = dict(HEADERS)
    domain = urllib.parse.urlparse(url).netloc
    h['Referer'] = f"https://{domain}/"
    session.cookies.set('xyt', '2', domain=domain)
    try:
        r = session.get(url, headers=h, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        form = soup.find('form')
        if form:
            data = {i.get('name'): i.get('value', '') for i in form.find_all('input') if i.get('name')}
            action = form.get('action') or url
            if action.startswith('?'):
                action = f"https://{domain}/hubcloud.php{action}"
            time.sleep(1.5)
            res = session.post(action, data=data, headers=h, timeout=15, stream=True)
            lnk = extract_real_video_link(res.text, res.url)
            if lnk: return lnk
        return extract_real_video_link(r.text, r.url) or f"ERR:{server_name}"
    except Exception as e:
        return f"ERR:{e}"


def auto_extract_10gbps(session, url):
    h = dict(HEADERS)
    h['Referer'] = url
    r = session.get(url, headers=h)
    soup = BeautifulSoup(r.text, 'html.parser')
    link = None

    # Pattern 1: anchor with 10gbps text or hubcloud.php href
    for a in soup.find_all('a', href=True):
        if '10gbps' in a.text.lower() or 'hubcloud.php' in a['href']:
            link = a['href']
            if link.startswith('?'):
                domain = urllib.parse.urlparse(url).netloc
                link = f"https://{domain}/hubcloud.php{link}"
            break

    # Pattern 2: var url = '...hubcloud.php...'
    if not link:
        m = re.search(r"var\s+url\s*=\s*['\"]([^'\"]+hubcloud\.php[^'\"]+)['\"]", r.text)
        if m:
            link = m.group(1)

    # FIX: Pattern 3: id="download" anchor (gamerxyt pattern)
    if not link:
        dl = soup.find('a', id='download', href=True)
        if dl:
            link = dl['href']

    # Pattern 4: any var url with full http
    if not link:
        m = re.search(r"var\s+url\s*=\s*['\"]([^'\"]{20,})['\"]", r.text)
        if m and m.group(1).startswith('http'):
            link = m.group(1)

    if link:
        return process_redirect_server(session, link, "10Gbps")
    return "ERR:10Gbps not found"


def deep_bypass(url, session):
    """Main bypass chain."""
    h = dict(HEADERS)

    # ── Step 1: cryptoinsights / gadgetsweb
    if 'cryptoinsights' in url or 'gadgetsweb' in url:
        domain = urllib.parse.urlparse(url).netloc
        session.cookies.set('xla', 's4t', domain=domain)
        r = session.get(url, headers=h)
        m = re.search(r"s\('o','([^']+)'", r.text)
        if m:
            try:
                d3 = rot13(base64.b64decode(base64.b64decode(m.group(1)).decode()).decode())
                next_url = base64.b64decode(json.loads(base64.b64decode(d3).decode())['o']).decode()
                return deep_bypass(next_url, session)
            except Exception as e:
                return f"ERR:decode:{e}"

    # ── Step 2: hblinks.dad
    if 'hblinks.dad' in url:
        r = session.get(url, headers=h)
        # FIX: Prefer hubdrive.space — simpler, more reliable
        m = re.search(r'href=["\']?(https?://hubdrive\.space/file/[a-z0-9]+)', r.text)
        if m:
            return deep_bypass(m.group(1), session)
        # Fallback: hubcloud.foo/drive/
        m = re.search(r'href=["\']?(https?://hubcloud\.[a-z]+/drive/[a-z0-9]+)', r.text)
        if m:
            return deep_bypass(m.group(1), session)
        # Fallback: any var url
        m = re.search(r"var\s+url\s*=\s*['\"]([^'\"]+)['\"]", r.text)
        if m:
            return deep_bypass(m.group(1), session)

    # ── Step 3: hubdrive.space/file/
    if 'hubdrive.space' in url:
        r = session.get(url, headers=h)
        m = re.search(r'(https?://hubcloud\.[a-z]+/drive/[a-z0-9]+)', r.text)
        if m:
            return deep_bypass(m.group(1), session)
        lnk = extract_real_video_link(r.text, r.url)
        if lnk:
            return lnk

    # ── Step 4: hubcdn.fans (direct CDN)
    if 'hubcdn.fans' in url:
        r = session.get(url, headers=h)
        lnk = extract_real_video_link(r.text, r.url)
        if lnk:
            return lnk
        return process_redirect_server(session, url, "HubCDN")

    # ── Step 5: hubcloud.foo/drive/ or similar
    if '/drive/' in url and 'hubcloud' in url:
        return auto_extract_10gbps(session, url)

    # ── FIX Step 6: gamerxyt.com (final hop for hubcloud.foo chain)
    if 'gamerxyt.com' in url:
        return process_redirect_server(session, url, "Gamerxyt")

    return url


# ── SCRAPING HELPERS ──────────────────────────────────────────────────────────
def _is_series(title):
    t = title.lower()
    return any(x in t for x in ['season', 'series', '| ep', 's01', 's02', 's03',
                                  's04', 's05', 's06', 's07', 's08', 's09', 's10'])


def _parse_card_list(soup):
    results = []
    seen = set()

    for li in soup.find_all('li', class_='thumb'):
        img_tag = li.find('img')
        figcap = li.find('figcaption')
        if not figcap:
            continue
        a_tag = figcap.find('a', href=True)
        p_tag = figcap.find('p')
        if not (a_tag and p_tag):
            continue
        link = a_tag.get('href', '')
        if 'hdhub4u' not in link or link in seen:
            continue
        seen.add(link)
        title = p_tag.get_text(strip=True)
        poster = img_tag.get('src', '') if img_tag else img_tag.get('data-src', '') if img_tag else ''
        if poster.startswith('//'):
            poster = 'https:' + poster
        results.append({'title': title, 'link': link, 'poster': poster, 'is_series': _is_series(title)})

    if not results:
        for art in soup.find_all('article'):
            a_tag = art.find('a', href=True)
            img_tag = art.find('img')
            title_tag = art.find(['h2', 'h3', 'h4', 'p'])
            if not (a_tag and title_tag):
                continue
            link = a_tag.get('href', '')
            if 'hdhub4u' not in link or link in seen:
                continue
            seen.add(link)
            title = title_tag.get_text(strip=True)
            poster = img_tag.get('src', '') if img_tag else ''
            if poster.startswith('//'):
                poster = 'https:' + poster
            results.append({'title': title, 'link': link, 'poster': poster, 'is_series': _is_series(title)})

    return results


def search_movies(query, session):
    for domain in HDHUB_DOMAINS:
        try:
            url = f"{domain}/?s={urllib.parse.quote(query)}"
            r = session.get(url, headers=HEADERS, timeout=12, allow_redirects=True)
            if r.status_code == 200:
                results = _parse_card_list(BeautifulSoup(r.text, 'html.parser'))
                if results:
                    return results
                if 'thumb' in r.text or '<article' in r.text:
                    return []
        except Exception:
            continue
    return []


def get_homepage_movies(session, page=1):
    for domain in HDHUB_DOMAINS:
        try:
            url = domain + '/' if page == 1 else f"{domain}/page/{page}/"
            r = session.get(url, headers=HEADERS, timeout=12, allow_redirects=True)
            if r.status_code == 200:
                results = _parse_card_list(BeautifulSoup(r.text, 'html.parser'))
                if results:
                    return results
        except Exception:
            continue
    return []


def get_content_info(url, session):
    try:
        r = session.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        soup = BeautifulSoup(r.text, 'html.parser')

        og = soup.find('meta', property='og:image')
        poster = og.get('content', '') if og else ''
        h1 = soup.find('h1')
        title = h1.get_text(strip=True) if h1 else url

        meta = {}
        for strong in soup.find_all('strong'):
            key = strong.get_text(strip=True).rstrip(':').strip()
            if key and len(key) < 30:
                sib = strong.next_sibling
                if sib:
                    val = re.sub(r'<[^>]+>', '', str(sib)).strip().lstrip(':').strip()
                    if val and len(val) < 200:
                        meta[key] = val

        all_links = []
        seen = set()
        for a in soup.find_all('a', href=True):
            href = a.get('href', '')
            label = a.get_text(strip=True)
            if not label or not href:
                continue
            if any(d in href for d in BYPASS_DOMS) and href not in seen:
                seen.add(href)
                all_links.append({'label': label, 'url': href})

        # FIX-4: Wider episode keywords
        ep_kw = [
            'episode', 'ep ', 'ep.', 'ep-', 'epis',
            'e01','e02','e03','e04','e05','e06','e07','e08','e09','e10',
            'e11','e12','e13','e14','e15','e16','e17','e18','e19','e20',
        ]
        q_kw = ['480p','720p','1080p','4k','2160p','hevc','x264','x265',
                'webrip','web-dl','bluray','hdtv','ds4k','hdcam','dvdrip','hdrip']

        episodes  = [l for l in all_links if any(p in l['label'].lower() for p in ep_kw)
                     and not any(p in l['label'].lower() for p in q_kw)]
        qualities = [l for l in all_links if any(p in l['label'].lower() for p in q_kw)]

        is_series = bool(episodes) or _is_series(title)

        if is_series and episodes:
            return {'title': title, 'poster': poster, 'is_series': True,
                    'episodes': episodes, 'qualities': qualities, 'meta': meta}
        elif qualities:
            return {'title': title, 'poster': poster, 'is_series': is_series,
                    'qualities': qualities, 'episodes': [], 'meta': meta}
        else:
            return {'title': title, 'poster': poster, 'is_series': is_series,
                    'qualities': all_links, 'episodes': [], 'meta': meta}

    except Exception as e:
        return {'error': str(e), 'title': '', 'poster': '',
                'is_series': False, 'qualities': [], 'episodes': [], 'meta': {}}


def extract_link(url, session):
    try:
        result = deep_bypass(url, session)
        if result and not str(result).startswith('ERR'):
            return {'success': True, 'link': result}
        return {'success': False, 'error': str(result)}
    except Exception as e:
        return {'success': False, 'error': str(e)}
