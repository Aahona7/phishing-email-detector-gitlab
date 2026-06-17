import re
import urllib.parse
import os
import dns.resolver
from bs4 import BeautifulSoup
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
import google.generativeai as genai

# Download NLTK data quietly if not present
def init_nltk():
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True)
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords', quiet=True)

init_nltk()

# List of popular domains to check typosquatting against
POPULAR_DOMAINS = [
    "google.com", "gmail.com", "yahoo.com", "outlook.com", "microsoft.com", 
    "paypal.com", "amazon.com", "apple.com", "netflix.com", "chase.com", 
    "bankofamerica.com", "wellsfargo.com", "facebook.com", "twitter.com", 
    "linkedin.com", "zoom.us", "adobe.com", "dropbox.com", "docusign.com"
]

# Suspicious TLDs
SUSPICIOUS_TLDS = {
    'xyz', 'top', 'club', 'work', 'click', 'support', 'info', 'biz', 
    'download', 'loan', 'gq', 'cf', 'tk', 'ml', 'date', 'faith', 'racing', 
    'cricket', 'win', 'space', 'accountant', 'bid', 'fit', 'science'
}

# Common link shortening services
SHORTENERS = {
    'bit.ly', 'tinyurl.com', 't.co', 'goo.gl', 'rebrand.ly', 'tiny.cc', 
    'is.gd', 'buff.ly', 'adf.ly', 'ow.ly', 'w.wiki', 'db.tt', 'git.io'
}

# Phishing and urgent terminology
URGENT_KEYWORDS = {
    'urgency': [
        'immediate action', 'act now', 'urgent', '24 hours', '48 hours', 'suspension', 
        'suspended', 'termination', 'disabled', 'unauthorized login', 'action required', 
        'final warning', 'consequences', 'restrict', 'restricted', 'limit', 'limited',
        'expires', 'expiring', 'hurry', 'immediately'
    ],
    'financial': [
        'wire transfer', 'bank details', 'lottery', 'gift card', 'refund', 'invoice', 
        'payment due', 'inheritance', 'million dollars', 'claim your prize', 'bitcoin', 
        'crypto', 'beneficiary', 'fund transfer', 'compensation', 'receipt'
    ],
    'security_credentials': [
        'verify your account', 'confirm password', 'security update', 'log in below', 
        'click here', 'restore access', 'update details', 'security check', 'reset password', 
        'security alert', 'unusual activity', 'verify identity'
    ]
}

# Dangerous file extensions
HIGH_RISK_EXTENSIONS = {
    '.exe', '.scr', '.bat', '.cmd', '.js', '.vbs', '.wsf', '.msi', '.jar', 
    '.pif', '.lnk', '.hta', '.cpl', '.gadget', '.ps1'
}
MEDIUM_RISK_EXTENSIONS = {
    '.zip', '.rar', '.7z', '.tar', '.gz', '.docm', '.xlsm', '.pptm'
}


def levenshtein_distance(s1, s2):
    """Calculate the Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


class EmailAnalyzer:
    def __init__(self, gemini_api_key=None):
        self.gemini_api_key = gemini_api_key
        if gemini_api_key:
            genai.configure(api_key=gemini_api_key)

    def extract_links_from_text(self, text):
        """Extract all URLs from plain text using regex."""
        url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
        urls = re.findall(url_pattern, text)
        return list(set(urls))

    def extract_links_from_html(self, html_content):
        """Extract links and anchor text from HTML using BeautifulSoup."""
        soup = BeautifulSoup(html_content, 'html.parser')
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href'].strip()
            anchor_text = a.get_text().strip()
            if href.startswith('http://') or href.startswith('https://'):
                links.append({
                    'url': href,
                    'text': anchor_text
                })
        return links

    def analyze_links(self, body_text, html_content=None):
        """
        Analyze links found in the body and HTML for suspicious characteristics.
        """
        results = {
            'score': 0,      # 0 to 100
            'threat_level': 'Safe',
            'findings': [],
            'extracted_links': []
        }
        
        raw_links = []
        html_links = []
        
        if html_content:
            html_links = self.extract_links_from_html(html_content)
            for link in html_links:
                raw_links.append(link['url'])
        
        # Merge with regex text links
        text_links = self.extract_links_from_text(body_text)
        for tl in text_links:
            if tl not in raw_links:
                raw_links.append(tl)
                html_links.append({'url': tl, 'text': ''})

        if not raw_links:
            return results

        suspicious_count = 0
        total_links = len(raw_links)
        
        for idx, link_item in enumerate(html_links):
            url = link_item['url']
            anchor_text = link_item['text']
            
            parsed = urllib.parse.urlparse(url)
            domain = parsed.netloc.lower()
            
            link_flags = []
            
            # 1. IP Address domain check
            ip_pattern = r'^(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?$'
            if re.match(ip_pattern, domain):
                link_flags.append("Uses raw IP address instead of domain name")
            
            # 2. Mismatched Link Text Check
            # If anchor text looks like a URL but actually points elsewhere
            if anchor_text:
                clean_anchor = anchor_text.lower().replace('https://', '').replace('http://', '').replace('www.', '')
                clean_url = url.lower().replace('https://', '').replace('http://', '').replace('www.', '')
                
                # Check if anchor is a domain/url and doesn't match the destination
                if ('.' in clean_anchor or '/' in clean_anchor) and clean_anchor.split('/')[0] != clean_url.split('/')[0]:
                    # Exclude general text like "Click here"
                    link_flags.append(f"Mismatched link: Display text suggests '{anchor_text}' but links to '{url}'")

            # 3. Protocol check
            if parsed.scheme == 'http':
                # Flag HTTP especially if it looks like a login or account page
                if any(x in url.lower() for x in ['login', 'signin', 'secure', 'account', 'bank', 'verify']):
                    link_flags.append("Uses insecure HTTP protocol for sensitive target page")
                else:
                    # Minor warning for plain HTTP
                    pass

            # 4. Shortener check
            if domain in SHORTENERS:
                link_flags.append(f"Uses a link shortening service ({domain}) to hide destination")

            # 5. Suspicious TLD check
            tld = domain.split('.')[-1] if '.' in domain else ''
            if tld in SUSPICIOUS_TLDS:
                link_flags.append(f"Uses a high-risk TLD (.{tld}) commonly associated with phishing")

            # 6. Excessive subdomains
            subdomains = domain.split('.')
            if len(subdomains) > 4: # e.g. login.secure.paypal.com.malicious.com (5 parts)
                link_flags.append(f"Excessive subdomains ({len(subdomains)-1}), potentially spoofing brands")

            if link_flags:
                suspicious_count += 1
                results['findings'].append({
                    'url': url,
                    'anchor_text': anchor_text,
                    'warnings': link_flags
                })
            
            results['extracted_links'].append({
                'url': url,
                'anchor_text': anchor_text,
                'is_suspicious': len(link_flags) > 0
            })

        # Calculate link score
        if total_links > 0:
            results['score'] = min(100, int((suspicious_count / total_links) * 100))
            if results['score'] > 50:
                results['threat_level'] = 'Danger'
            elif results['score'] > 0:
                results['threat_level'] = 'Caution'
        
        return results

    def analyze_sender(self, from_header):
        """
        Analyze the sender name and email domain for spoofing or typosquatting.
        Example: PayPal Support <service@paypa1.com>
        """
        results = {
            'score': 0,
            'threat_level': 'Safe',
            'sender_name': '',
            'sender_email': '',
            'sender_domain': '',
            'findings': []
        }

        if not from_header:
            return results

        # Parse From Header
        # Standard format: "Name" <email@domain.com> or email@domain.com
        email_match = re.search(r'<([^>]+)>', from_header)
        if email_match:
            sender_email = email_match.group(1).strip()
            sender_name = from_header.replace(email_match.group(0), '').strip().strip('"\'')
        else:
            sender_email = from_header.strip()
            sender_name = ""

        results['sender_email'] = sender_email
        results['sender_name'] = sender_name

        if '@' not in sender_email:
            results['score'] = 100
            results['threat_level'] = 'Danger'
            results['findings'].append("Invalid sender email format")
            return results

        domain = sender_email.split('@')[-1].lower().strip()
        results['sender_domain'] = domain

        # 1. Lookalike Brand Check (Typosquatting) using Levenshtein Distance
        # Check domain parts (e.g. paypa1 from paypa1.com)
        domain_name = domain.split('.')[0] if '.' in domain else domain
        
        is_typosquatted = False
        target_brand = ""
        
        for brand_domain in POPULAR_DOMAINS:
            brand_name = brand_domain.split('.')[0]
            
            # Check Levenshtein distance on full domain
            dist_full = levenshtein_distance(domain, brand_domain)
            # Check Levenshtein distance on primary domain name
            dist_name = levenshtein_distance(domain_name, brand_name)
            
            # If distance is small but not 0 (exact match)
            if 0 < dist_full <= 2 or (0 < dist_name <= 1 and len(brand_name) > 3):
                # Ensure it's not a subdomain match that is legitimate, though subdomains are handled
                is_typosquatted = True
                target_brand = brand_domain
                break
            
            # Sub-domain brand spoofing check
            # e.g., paypal.com.attacker.com
            if brand_name in domain and domain != brand_domain and not domain.endswith('.' + brand_domain):
                is_typosquatted = True
                target_brand = brand_domain
                break

        if is_typosquatted:
            results['score'] = max(results['score'], 85)
            results['findings'].append(f"Typosquatting/Spoofing warning: Domain '{domain}' is suspiciously similar to major brand '{target_brand}'")

        # 2. Display Name Mismatch Check
        # e.g., Display Name = "Google Support", Email = "attacker@xyz.com"
        if sender_name:
            sender_name_lower = sender_name.lower()
            for brand_domain in POPULAR_DOMAINS:
                brand_name = brand_domain.split('.')[0]
                # If display name mentions PayPal/Google, but email domain is unrelated
                if brand_name in sender_name_lower and brand_name not in domain:
                    # Exclude matches if the sender is actually from Gmail or Outlook sending standard emails
                    # (though phishing emails commonly use gmail to spoof "PayPal Invoice")
                    results['score'] = max(results['score'], 60)
                    results['findings'].append(f"Name-Email Mismatch: Display name contains '{sender_name}' but email is sent from unrelated domain '{domain}'")
                    break

        # 3. DNS Record Validation (Check if MX records exist)
        try:
            dns.resolver.resolve(domain, 'MX')
        except dns.resolver.NXDOMAIN:
            # Domain name does not exist at all in the DNS registry
            results['score'] = max(results['score'], 75)
            results['findings'].append(f"Non-existent Domain: Sender domain '{domain}' does not exist in the DNS registry, indicating a fake email address")
        except dns.resolver.NoAnswer:
            # Domain exists but has no MX records configured to send/receive mail
            results['score'] = max(results['score'], 45)
            results['findings'].append(f"No Mail Records: Domain '{domain}' exists but has no active MX (Mail Exchange) records configured")
        except (dns.exception.Timeout, Exception):
            # Timeout or general connection failure (e.g. offline mode) - do not penalize
            pass

        # Determine level
        if results['score'] >= 75:
            results['threat_level'] = 'Danger'
        elif results['score'] >= 40:
            results['threat_level'] = 'Caution'

        return results

    def analyze_urgency(self, body_text):
        """
        Analyze the language in the body text for urgency, threats, and phishing tactics.
        """
        results = {
            'score': 0,
            'threat_level': 'Safe',
            'findings': [],
            'flagged_phrases': [],
            'metrics': {
                'urgency_matches': 0,
                'financial_matches': 0,
                'security_matches': 0,
                'sentence_count': 0
            }
        }

        if not body_text or not body_text.strip():
            return results

        # NLP processing using NLTK
        sentences = sent_tokenize(body_text)
        results['metrics']['sentence_count'] = len(sentences)

        urgency_matches = []
        financial_matches = []
        security_matches = []

        # Scan text for our keyword lists (case-insensitive search for phrases/keywords)
        body_text_lower = body_text.lower()
        
        # Find matches and assign to sentences
        for category, terms in URGENT_KEYWORDS.items():
            for term in terms:
                # Use regex word boundaries for match accuracy
                pattern = rf'\b{re.escape(term)}\b'
                matches = re.findall(pattern, body_text_lower)
                if matches:
                    matched_info = {
                        'term': term,
                        'count': len(matches),
                        'category': category
                    }
                    
                    if category == 'urgency':
                        urgency_matches.append(matched_info)
                    elif category == 'financial':
                        financial_matches.append(matched_info)
                    elif category == 'security_credentials':
                        security_matches.append(matched_info)
                    
                    results['flagged_phrases'].append(term)

        results['metrics']['urgency_matches'] = sum(m['count'] for m in urgency_matches)
        results['metrics']['financial_matches'] = sum(m['count'] for m in financial_matches)
        results['metrics']['security_matches'] = sum(m['count'] for m in security_matches)

        # Highlight sentences containing suspicious phrases
        flagged_sentences = []
        for sentence in sentences:
            sentence_lower = sentence.lower()
            reasons = []
            for category, terms in URGENT_KEYWORDS.items():
                for term in terms:
                    if re.search(rf'\b{re.escape(term)}\b', sentence_lower):
                        reasons.append(term)
            
            if reasons:
                flagged_sentences.append({
                    'text': sentence.strip(),
                    'triggers': list(set(reasons))
                })

        results['findings'] = flagged_sentences

        # Calculate NLP Threat Score
        # Weight vectors: Urgency (35%), Security Credentials (45%), Financial (20%)
        trigger_count = (results['metrics']['urgency_matches'] * 20 + 
                         results['metrics']['security_matches'] * 25 + 
                         results['metrics']['financial_matches'] * 15)
        
        # Normalize score based on text length (phishing emails are usually short and dense)
        # 1-3 triggers in a short email is highly suspicious
        if len(sentences) > 0:
            density_factor = max(1.0, 5.0 / len(sentences)) # boost score for short, dense emails
            results['score'] = min(100, int(trigger_count * density_factor))
        else:
            results['score'] = min(100, trigger_count)

        if results['score'] >= 60:
            results['threat_level'] = 'Danger'
        elif results['score'] > 15:
            results['threat_level'] = 'Caution'

        return results

    def analyze_attachments(self, attachment_list):
        """
        Analyze attachment metadata (filenames and sizes) for security threats.
        Format: [{'filename': 'invoice.pdf.exe', 'size': 12345, 'content_type': '...'}]
        """
        results = {
            'score': 0,
            'threat_level': 'Safe',
            'findings': []
        }

        if not attachment_list:
            return results

        high_risk_count = 0
        medium_risk_count = 0

        for file_info in attachment_list:
            filename = file_info.get('filename', '').strip()
            if not filename:
                continue

            name_lower = filename.lower()
            _, ext = os.path.splitext(name_lower)
            
            file_flags = []
            
            # Double extension check (e.g., invoice.pdf.exe)
            double_ext_match = re.search(r'\.[a-z0-9]+\.([a-z0-9]+)$', name_lower)
            if double_ext_match:
                file_flags.append("Double file extension (potential masquerading technique)")
                ext = '.' + double_ext_match.group(1)

            # Check Risk Level
            if ext in HIGH_RISK_EXTENSIONS:
                high_risk_count += 1
                file_flags.append(f"High-risk executable extension '{ext}' (directly runnable code)")
            elif ext in MEDIUM_RISK_EXTENSIONS:
                medium_risk_count += 1
                if ext == '.docm' or ext == '.xlsm' or ext == '.pptm':
                    file_flags.append(f"Macro-enabled Office document '{ext}' (often used to deliver malware)")
                elif ext in ['.zip', '.rar', '.7z']:
                    file_flags.append(f"Archive extension '{ext}' (used to bypass scanning systems)")
                else:
                    file_flags.append(f"Medium-risk file format '{ext}' (should verify content)")

            # Space masquerading check (e.g., invoice                     .exe)
            if '      ' in filename:
                file_flags.append("Suspicious use of multiple spaces in name to hide extension")

            if file_flags:
                results['findings'].append({
                    'filename': filename,
                    'warnings': file_flags,
                    'size': file_info.get('size', 0),
                    'risk': 'High' if ext in HIGH_RISK_EXTENSIONS else 'Medium'
                })

        # Calculate Score
        if high_risk_count > 0:
            results['score'] = 100
            results['threat_level'] = 'Danger'
        elif medium_risk_count > 0:
            results['score'] = 50
            results['threat_level'] = 'Caution'

        return results

    def run_full_analysis(self, body_text, from_header=None, html_content=None, attachments=None):
        """
        Execute all analysis modules and compile aggregate threats.
        """
        links_res = self.analyze_links(body_text, html_content)
        sender_res = self.analyze_sender(from_header)
        nlp_res = self.analyze_urgency(body_text)
        attachments_res = self.analyze_attachments(attachments)

        # Aggregate Score Computation
        # Weights: Sender (30%), Links (35%), NLP (20%), Attachments (15%)
        # Note: If any single category is 100/Danger, the final score should reflect a high danger.
        weights = [
            (sender_res['score'], 0.30),
            (links_res['score'], 0.35),
            (nlp_res['score'], 0.20),
            (attachments_res['score'], 0.15)
        ]
        
        weighted_score = sum(score * weight for score, weight in weights)
        
        # Max override: if sender or links is a severe threat, scale final score higher
        max_threat_score = max(sender_res['score'], links_res['score'], attachments_res['score'])
        final_score = int(max(weighted_score, max_threat_score * 0.85))

        if final_score >= 70:
            overall_threat = 'Danger'
        elif final_score >= 35:
            overall_threat = 'Caution'
        else:
            overall_threat = 'Safe'

        summary = {
            'final_score': final_score,
            'overall_threat': overall_threat,
            'modules': {
                'links': links_res,
                'sender': sender_res,
                'nlp': nlp_res,
                'attachments': attachments_res
            }
        }

        # Generate Explanation
        api_key = self.gemini_api_key or os.getenv('GEMINI_API_KEY')
        explanation = self.generate_explanation(summary, body_text, api_key)
        summary['explanation'] = explanation

        return summary

    def generate_explanation(self, summary, body_text, api_key):
        """
        Generates the explanation using Gemini API, or falls back to rules if unavailable.
        """
        # Formulate rule-based fallback first
        fallback_reasons = []
        modules = summary['modules']

        # Gather main warnings
        if modules['sender']['findings']:
            fallback_reasons.append(f"**Sender Identity Issues**: {modules['sender']['findings'][0]}")
        if modules['links']['findings']:
            fallback_reasons.append(f"**Suspicious Links**: Found {len(modules['links']['findings'])} flagged URLs (e.g., {modules['links']['findings'][0]['url']})")
        if modules['nlp']['metrics']['urgency_matches'] > 0 or modules['nlp']['metrics']['security_matches'] > 0:
            fallback_reasons.append("**Urgent/Phishing Tone**: Detects urgent calls-to-action or requests for account/credential verification")
        if modules['attachments']['findings']:
            fallback_reasons.append(f"**Hazardous Attachments**: {modules['attachments']['findings'][0]['warnings'][0]}")

        fallback_explanation = "This email is suspicious because:\n\n"
        if fallback_reasons:
            fallback_explanation += "\n".join([f"- {r}" for r in fallback_reasons])
        else:
            fallback_explanation = "This email appears safe based on our standard rules, as we detected no suspicious domains, links, high-pressure language, or dangerous attachments."

        if not api_key:
            return fallback_explanation + "\n\n*(Note: Add a Gemini API key in the settings panel to enable detailed, AI-powered threat explanations.)*"

        # Prompt for Gemini
        prompt = f"""
You are a Cyber Security Analyst specializing in Email Security.
Analyze the following email analysis reports and the raw email text. Write a short, highly professional explanation in Markdown format starting with the phrase "This email is suspicious because..." explaining exactly why this email presents a risk, or why it seems safe.

---
ANALYSIS RESULTS SUMMARY:
- Overall Score: {summary['final_score']}/100
- Threat Level: {summary['overall_threat']}
- Sender Findings: {modules['sender']['findings']}
- Link Findings: { [f['warnings'] for f in modules['links']['findings']] }
- NLP Language Triggers: {modules['nlp']['flagged_phrases']}
- Attachment Warnings: { [f['warnings'] for f in modules['attachments']['findings']] }

---
EMAIL BODY TEXT:
\"\"\"{body_text[:1500]}\"\"\"

Provide your breakdown of the key threats concisely in 3-4 bullet points under the heading "This email is suspicious because...". Ensure your tone is clear, analytical, and instructive. Keep it under 200 words.
"""

        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            # Fallback to local rule-based if LLM call fails
            return fallback_explanation + f"\n\n*(Failed to contact Gemini API: {str(e)}. Showing rule-based results instead.)*"
