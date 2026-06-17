import pytest
from detector import levenshtein_distance, EmailAnalyzer

def test_levenshtein_distance():
    # Exact match
    assert levenshtein_distance("paypal", "paypal") == 0
    # Substitution
    assert levenshtein_distance("paypa1", "paypal") == 1
    # Insertion
    assert levenshtein_distance("paypall", "paypal") == 1
    # Deletion
    assert levenshtein_distance("paypa", "paypal") == 1
    # Drastic difference
    assert levenshtein_distance("google", "microsoft") > 4

def test_analyze_links():
    analyzer = EmailAnalyzer()
    
    # Insecure link in plain body
    body = "Click here to login: http://192.168.0.1/verify"
    res = analyzer.analyze_links(body)
    assert res['threat_level'] in ['Caution', 'Danger']
    assert any("IP address" in w for w in res['findings'][0]['warnings'])
    
    # Typosquatted text mismatch link in HTML body
    html_content = '<a href="http://paypa1-security.com">paypal.com</a>'
    res = analyzer.analyze_links("Check link", html_content)
    assert res['threat_level'] in ['Caution', 'Danger']
    # Check mismatched link text warning is present
    assert any("Mismatched" in w for w in res['findings'][0]['warnings'])

def test_analyze_sender():
    analyzer = EmailAnalyzer()
    
    # Exact match for popular domain should be safe
    safe_from = "PayPal Security <support@paypal.com>"
    res = analyzer.analyze_sender(safe_from)
    assert res['threat_level'] == 'Safe'
    
    # Typosquatted domain
    phish_from = "PayPal Alert <security@paypa1.com>"
    res = analyzer.analyze_sender(phish_from)
    assert res['threat_level'] in ['Caution', 'Danger']
    assert any("Typosquatting" in w for w in res['findings'])

    # Display name mismatch
    mismatch_from = "Google Support <hacker123@xyz.com>"
    res = analyzer.analyze_sender(mismatch_from)
    assert res['threat_level'] in ['Caution', 'Danger']
    assert any("Mismatch" in w for w in res['findings'])

def test_analyze_urgency():
    analyzer = EmailAnalyzer()
    
    # Normal email
    normal_text = "Hi team, the weekly meeting has been moved to Thursday at 10 AM. Let me know if you can make it."
    res = analyzer.analyze_urgency(normal_text)
    assert res['threat_level'] == 'Safe'
    assert res['score'] < 10

    # Phishing email with high urgency
    phish_text = "Urgent: Your account is suspended immediately! Click here to verify your account or password within 24 hours to restore access."
    res = analyzer.analyze_urgency(phish_text)
    assert res['threat_level'] in ['Caution', 'Danger']
    assert res['score'] > 40
    assert len(res['flagged_phrases']) > 0

def test_analyze_attachments():
    analyzer = EmailAnalyzer()
    
    # No attachments
    res = analyzer.analyze_attachments([])
    assert res['threat_level'] == 'Safe'
    
    # Safe attachments
    safe_atts = [
        {'filename': 'invoice.pdf', 'size': 1024, 'content_type': 'application/pdf'},
        {'filename': 'presentation.pptx', 'size': 2048, 'content_type': 'application/vnd.openxmlformats-officedocument'}
    ]
    res = analyzer.analyze_attachments(safe_atts)
    assert res['threat_level'] == 'Safe'

    # Dangerous attachment (high risk)
    phish_atts = [
        {'filename': 'document.pdf.exe', 'size': 512, 'content_type': 'application/octet-stream'}
    ]
    res = analyzer.analyze_attachments(phish_atts)
    assert res['threat_level'] == 'Danger'
    assert any("Double file extension" in w for w in res['findings'][0]['warnings'])
    assert any("High-risk" in w for w in res['findings'][0]['warnings'])
