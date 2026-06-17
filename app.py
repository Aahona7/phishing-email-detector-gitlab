import os
import email
from email.header import decode_header
import imaplib
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from detector import EmailAnalyzer

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24))

def get_decoded_header(msg, header_name):
    """Safely decode email header encoding (e.g. UTF-8 base64)."""
    val = msg.get(header_name, '')
    if not val:
        return ''
    try:
        decoded = decode_header(val)
        header_parts = []
        for text, encoding in decoded:
            if isinstance(text, bytes):
                header_parts.append(text.decode(encoding or 'utf-8', errors='ignore'))
            else:
                header_parts.append(text)
        return ''.join(header_parts)
    except Exception:
        return str(val)

def parse_email_message(msg):
    """Recursively parse multi-part or single-part email messages."""
    from_header = get_decoded_header(msg, 'From')
    subject_header = get_decoded_header(msg, 'Subject')
    date_header = get_decoded_header(msg, 'Date')
    
    body = ""
    html_content = ""
    attachments = []
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))
            
            # Check if it's an attachment
            if "attachment" in content_disposition or part.get_filename():
                filename = part.get_filename()
                if filename:
                    try:
                        decoded = decode_header(filename)
                        filename_decoded, encoding = decoded[0]
                        if isinstance(filename_decoded, bytes):
                            filename = filename_decoded.decode(encoding or 'utf-8', errors='ignore')
                    except Exception:
                        pass
                    
                    payload = part.get_payload(decode=True)
                    size = len(payload) if payload else 0
                    attachments.append({
                        'filename': filename,
                        'size': size,
                        'content_type': content_type
                    })
            else:
                # Text content parts
                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        body += payload.decode(part.get_content_charset() or 'utf-8', errors='ignore')
                elif content_type == "text/html":
                    payload = part.get_payload(decode=True)
                    if payload:
                        html_content += payload.decode(part.get_content_charset() or 'utf-8', errors='ignore')
    else:
        content_type = msg.get_content_type()
        payload = msg.get_payload(decode=True)
        if payload:
            text = payload.decode(msg.get_content_charset() or 'utf-8', errors='ignore')
            if content_type == "text/html":
                html_content = text
                # Strip text for plain body
                body = BeautifulSoup(text, 'html.parser').get_text()
            else:
                body = text

    # Final cleanup fallbacks
    if not body and html_content:
        body = BeautifulSoup(html_content, 'html.parser').get_text()

    return {
        'from_header': from_header,
        'subject': subject_header,
        'date': date_header,
        'body': body,
        'html_content': html_content,
        'attachments': attachments
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    """Handles EML files uploaded via form-data OR plain texts via JSON."""
    if 'email_file' in request.files:
        file = request.files['email_file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        gemini_key = request.form.get('gemini_key', '').strip()
        
        try:
            raw_content = file.read()
            msg = email.message_from_bytes(raw_content)
            parsed = parse_email_message(msg)
            
            analyzer = EmailAnalyzer(gemini_api_key=gemini_key if gemini_key else None)
            analysis = analyzer.run_full_analysis(
                body_text=parsed['body'],
                from_header=parsed['from_header'],
                html_content=parsed['html_content'],
                attachments=parsed['attachments']
            )
            
            return jsonify({
                'success': True,
                'email_details': {
                    'subject': parsed['subject'] or '(No Subject)',
                    'sender': parsed['from_header'] or '(No Sender)',
                    'date': parsed['date'] or 'N/A',
                    'body': parsed['body'],
                    'html_content': parsed['html_content'],
                    'attachments': parsed['attachments']
                },
                'analysis': analysis
            })
        except Exception as e:
            return jsonify({'error': f'Failed to analyze EML: {str(e)}'}), 500

    # JSON post route
    data = request.json or {}
    body_text = data.get('body', '').strip()
    from_header = data.get('from_header', '').strip()
    html_content = data.get('html_content', '').strip()
    attachments = data.get('attachments', [])
    gemini_key = data.get('gemini_key', '').strip()
    
    if not body_text:
        return jsonify({'error': 'Email body content is required for analysis'}), 400

    try:
        analyzer = EmailAnalyzer(gemini_api_key=gemini_key if gemini_key else None)
        analysis = analyzer.run_full_analysis(
            body_text=body_text,
            from_header=from_header,
            html_content=html_content,
            attachments=attachments
        )
        return jsonify({
            'success': True,
            'email_details': {
                'subject': data.get('subject', 'Manual Scan'),
                'sender': from_header or '(No Sender)',
                'date': 'N/A',
                'body': body_text,
                'html_content': html_content,
                'attachments': attachments
            },
            'analysis': analysis
        })
    except Exception as e:
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

@app.route('/imap/connect', methods=['POST'])
def imap_connect():
    """Establish IMAP connection and list recent email headers."""
    data = request.json or {}
    host = data.get('host', '').strip()
    port = data.get('port', 993)
    email_addr = data.get('email', '').strip()
    password = data.get('password', '').strip()

    if not all([host, port, email_addr, password]):
        return jsonify({'error': 'Missing IMAP connection details'}), 400

    try:
        mail = imaplib.IMAP4_SSL(host, int(port))
        mail.login(email_addr, password)
        mail.select('INBOX', readonly=True)
        
        status, messages = mail.search(None, 'ALL')
        if status != 'OK':
            return jsonify({'error': 'Failed to query INBOX'}), 500
            
        msg_ids = messages[0].split()
        # Fetch last 10 messages
        recent_ids = msg_ids[-10:]
        recent_ids.reverse() # Newest first
        
        email_list = []
        for msg_id in recent_ids:
            res, header_data = mail.fetch(msg_id, '(BODY[HEADER.FIELDS (SUBJECT FROM DATE)])')
            if res != 'OK' or not header_data[0]:
                continue
                
            header_text = header_data[0][1].decode('utf-8', errors='ignore')
            msg = email.message_from_string(header_text)
            
            subject = get_decoded_header(msg, 'Subject')
            sender = get_decoded_header(msg, 'From')
            date = get_decoded_header(msg, 'Date')
            
            email_list.append({
                'uid': msg_id.decode('utf-8'),
                'subject': subject or '(No Subject)',
                'sender': sender or '(No Sender)',
                'date': date or '(No Date)'
            })
            
        mail.close()
        mail.logout()
        return jsonify({'success': True, 'emails': email_list})
    except Exception as e:
        return jsonify({'error': f'IMAP Connection failed: {str(e)}'}), 500

@app.route('/imap/fetch', methods=['POST'])
def imap_fetch():
    """Fetch complete email content by UID and analyze it."""
    data = request.json or {}
    host = data.get('host', '').strip()
    port = data.get('port', 993)
    email_addr = data.get('email', '').strip()
    password = data.get('password', '').strip()
    uid = data.get('uid', '').strip()
    gemini_key = data.get('gemini_key', '').strip()

    if not all([host, port, email_addr, password, uid]):
        return jsonify({'error': 'Missing parameters to fetch email'}), 400

    try:
        mail = imaplib.IMAP4_SSL(host, int(port))
        mail.login(email_addr, password)
        mail.select('INBOX', readonly=True)

        res, msg_data = mail.fetch(uid.encode('utf-8'), '(RFC822)')
        if res != 'OK' or not msg_data[0]:
            return jsonify({'error': 'Failed to fetch email body'}), 500

        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)
        parsed = parse_email_message(msg)

        analyzer = EmailAnalyzer(gemini_api_key=gemini_key if gemini_key else None)
        analysis = analyzer.run_full_analysis(
            body_text=parsed['body'],
            from_header=parsed['from_header'],
            html_content=parsed['html_content'],
            attachments=parsed['attachments']
        )

        mail.close()
        mail.logout()

        return jsonify({
            'success': True,
            'email_details': {
                'subject': parsed['subject'] or '(No Subject)',
                'sender': parsed['from_header'] or '(No Sender)',
                'date': parsed['date'] or 'N/A',
                'body': parsed['body'],
                'html_content': parsed['html_content'],
                'attachments': parsed['attachments']
            },
            'analysis': analysis
        })
    except Exception as e:
        return jsonify({'error': f'Failed to process email fetch: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
