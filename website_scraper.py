# /website_scraper.py
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def scrape_company_pages(website_url):
    """(/website_scraper.scrape_company_pages) - Scrape homepage, about, team, and contact pages"""
    results = {
        'homepage': None,
        'about_page': None, 
        'team_page': None,
        'contact_page': None,  # NEW
        'employee_count': None,
        'business_description': None,
        'error': None
    }
    
    try:
        # Scrape homepage first
        homepage_data = scrape_single_page(website_url)
        if not homepage_data:
            results['error'] = 'Could not access homepage'
            return results
            
        results['homepage'] = homepage_data
        results['business_description'] = extract_business_description(homepage_data['text'])
        
        # Look for about, team, and contact pages
        about_url = find_about_page(homepage_data['soup'], website_url)
        if about_url:
            about_data = scrape_single_page(about_url)
            if about_data:
                results['about_page'] = about_data
                
        team_url = find_team_page(homepage_data['soup'], website_url)  
        if team_url:
            team_data = scrape_single_page(team_url)
            if team_data:
                results['team_page'] = team_data
        
        # NEW: Contact page
        contact_url = find_contact_page(homepage_data['soup'], website_url)
        if contact_url:
            contact_data = scrape_single_page(contact_url)
            if contact_data:
                results['contact_page'] = contact_data
                
        return results
        
    except Exception as e:
        results['error'] = f"Scraping error: {str(e)}"
        return results
    

def find_contact_page(soup, base_url):
    """(/website_scraper.find_contact_page) - Find the contact page URL"""
    contact_keywords = ['contact', 'contact-us', 'contact_us', 'get-in-touch', 'reach-us']
    
    for link in soup.find_all('a', href=True):
        href = link.get('href', '').lower()
        link_text = link.get_text().lower().strip()
        
        if any(keyword in href for keyword in contact_keywords) or \
           any(keyword in link_text.replace(' ', '-') for keyword in contact_keywords):
            full_url = urljoin(base_url, link['href'])
            return full_url
            
    return None


def scrape_single_page(url):
    """(/website_scraper.scrape_single_page) - Scrape with better error handling"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # Handle unusual domains better
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        # Try HTTPS first with SSL verification
        try:
            response = requests.get(
                url, 
                headers=headers, 
                timeout=15,
                allow_redirects=True,
                verify=True  # SSL verification enabled
            )
            response.raise_for_status()
            
        except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as e:
            print(f"  ⚠️ SSL/Connection issue, trying without SSL verification...")
            
            # Retry without SSL verification for misconfigured certificates
            response = requests.get(
                url, 
                headers=headers, 
                timeout=15,
                allow_redirects=True,
                verify=False  # Disable SSL verification
            )
            response.raise_for_status()
            
        except requests.exceptions.RequestException as e:
            # If HTTPS fails completely, try HTTP
            if url.startswith('https://'):
                print(f"  ⚠️ HTTPS failed, trying HTTP...")
                http_url = url.replace('https://', 'http://')
                response = requests.get(
                    http_url, 
                    headers=headers, 
                    timeout=15,
                    allow_redirects=True
                )
                response.raise_for_status()
            else:
                raise
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
            
        # Get clean text
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return {
            'url': url,
            'text': clean_text,
            'soup': soup,
            'title': soup.title.string if soup.title else None
        }
        
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None


def find_about_page(soup, base_url):
    """(/website_scraper.find_about_page) - Find the about page URL"""
    about_keywords = ['about', 'about-us', 'about_us', 'who-we-are', 'company', 'our-story']
    
    # Look for links containing about keywords
    for link in soup.find_all('a', href=True):
        href = link.get('href', '').lower()
        link_text = link.get_text().lower().strip()
        
        # Check href and link text for about keywords
        if any(keyword in href for keyword in about_keywords) or \
           any(keyword in link_text.replace(' ', '-') for keyword in about_keywords):
            full_url = urljoin(base_url, link['href'])
            return full_url
            
    return None

def find_team_page(soup, base_url):
    """(/website_scraper.find_team_page) - Find the team page URL"""
    team_keywords = ['team', 'our-team', 'staff', 'people', 'meet-the-team', 'employees']
    
    for link in soup.find_all('a', href=True):
        href = link.get('href', '').lower()
        link_text = link.get_text().lower().strip()
        
        if any(keyword in href for keyword in team_keywords) or \
           any(keyword in link_text.replace(' ', '-') for keyword in team_keywords):
            full_url = urljoin(base_url, link['href'])
            return full_url
            
    return None
def extract_employee_mentions(text):
    """(/website_scraper.extract_employee_mentions) - Find mentions of employee count with source context"""
    if not text:
        return None
        
    # Patterns to look for employee counts
    patterns = [
        r'team of (\d+)',
        r'(\d+) employees?',  
        r'(\d+) staff',
        r'(\d+) people',
        r'(\d+)\+ employees?',
        r'over (\d+) employees?',
        r'more than (\d+) employees?',
        r'(\d+) strong team',
        r'workforce of (\d+)',
        r'employs (\d+)'
    ]
    
    text_lower = text.lower()
    found_counts = []
    
    for pattern in patterns:
        matches = re.finditer(pattern, text_lower)  # Use finditer to get positions
        for match in matches:
            try:
                count = int(match.group(1))
                if 1 <= count <= 10000:  # Reasonable range
                    # Get surrounding context (50 chars before and after)
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    context = text[start:end].replace('\n', ' ').strip()
                    
                    found_counts.append({
                        'count': count,
                        'context': context,
                        'pattern': pattern
                    })
            except ValueError:
                continue
                
    if found_counts:
        # Return the most commonly mentioned count with its context
        most_common = max(set([item['count'] for item in found_counts]), 
                         key=lambda x: len([item for item in found_counts if item['count'] == x]))
        
        # Find the context for this count
        context_for_count = next(item['context'] for item in found_counts if item['count'] == most_common)
        
        return {
            'count': most_common,
            'source_text': context_for_count,
            'all_matches': found_counts  # For debugging
        }
        
    return None

def extract_business_description(text):
    """(/website_scraper.extract_business_description) - Extract business description from homepage"""
    if not text:
        return None
        
    # Get first few paragraphs as they usually contain business description
    lines = text.split('\n')
    meaningful_lines = [line for line in lines if len(line.strip()) > 50]
    
    if meaningful_lines:
        # Return first 500 characters of meaningful content
        description = ' '.join(meaningful_lines[:3])
        return description[:500] + '...' if len(description) > 500 else description
        
    return None