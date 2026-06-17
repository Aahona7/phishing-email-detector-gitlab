/* ==========================================================================
   SentryMail - Core Frontend JS Logic
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
    // --- Global State ---
    let selectedEmlFile = null;
    let imapCredentials = null; // Store temporarily in memory for subsequent fetch requests

    // --- DOM Elements ---
    const geminiKeyInput = document.getElementById('gemini-api-key');
    
    // Tab selectors
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    // Paste Form
    const pasteForm = document.getElementById('paste-form');
    
    // EML Upload
    const dragDropZone = document.getElementById('drag-drop-zone');
    const emlFileInput = document.getElementById('eml-file-input');
    const selectedFileName = document.getElementById('selected-file-name');
    const uploadSubmitBtn = document.getElementById('upload-submit-btn');
    
    // IMAP Connection
    const imapPreset = document.getElementById('imap-preset');
    const imapHost = document.getElementById('imap-host');
    const imapPort = document.getElementById('imap-port');
    const imapEmail = document.getElementById('imap-email');
    const imapPassword = document.getElementById('imap-password');
    const imapLoginForm = document.getElementById('imap-login-form');
    const imapMailListContainer = document.querySelector('.imap-mail-list-container');
    const imapEmailsBody = document.getElementById('imap-emails-body');
    const imapDisconnectBtn = document.getElementById('imap-disconnect-btn');

    // Result States
    const resultsIdle = document.getElementById('results-idle');
    const resultsScanning = document.getElementById('results-scanning');
    const resultsComplete = document.getElementById('results-complete');
    const resultsPanel = document.getElementById('results-panel');
    const scannerStatus = document.getElementById('scanner-status');
    const scannerProgress = document.getElementById('scanner-progress');
    const scanLogs = document.getElementById('scan-logs');
    
    // Result Details
    const resultScoreVal = document.getElementById('result-score-val');
    const resultThreatBadge = document.getElementById('result-threat-badge');
    const gaugeFillArc = document.getElementById('gauge-fill-arc');
    const resultMetaSubject = document.getElementById('result-meta-subject');
    const resultMetaSender = document.getElementById('result-meta-sender');
    const resultMetaDate = document.getElementById('result-meta-date');
    const resultAiExplanation = document.getElementById('result-ai-explanation');
    
    // Modular Results Tabs
    const modTabBtns = document.querySelectorAll('.mod-tab-btn');
    const modContents = document.querySelectorAll('.mod-content');
    
    // Badge Indicators
    const badgeSender = document.getElementById('badge-sender');
    const badgeLinks = document.getElementById('badge-links');
    const badgeUrgency = document.getElementById('badge-urgency');
    const badgeAttachments = document.getElementById('badge-attachments');

    // Details containers
    const senderDetailsContainer = document.getElementById('sender-details-container');
    const linksDetailsContainer = document.getElementById('links-details-container');
    const urgencyDetailsContainer = document.getElementById('urgency-details-container');
    const attachmentsDetailsContainer = document.getElementById('attachments-details-container');
    
    // Mini NLP metrics
    const nlpMetricUrgency = document.getElementById('nlp-metric-urgency');
    const nlpMetricCredentials = document.getElementById('nlp-metric-credentials');
    const nlpMetricFinancial = document.getElementById('nlp-metric-financial');
    
    // Email Content Viewer
    const viewTabBtns = document.querySelectorAll('.view-tab-btn');
    const viewContents = document.querySelectorAll('.view-content');
    const emailRawTextContent = document.getElementById('email-raw-text-content');
    const emailHtmlIframe = document.getElementById('email-html-iframe');
    
    const resetScanBtn = document.getElementById('reset-scan-btn');

    // Save/Restore Gemini API Key from session storage
    if (sessionStorage.getItem('gemini_api_key')) {
        geminiKeyInput.value = sessionStorage.getItem('gemini_api_key');
    }
    geminiKeyInput.addEventListener('change', () => {
        sessionStorage.setItem('gemini_api_key', geminiKeyInput.value);
    });

    // --- Tab Switcher Logic ---
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');
            
            // Toggle buttons
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Toggle panels
            tabContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === targetTab) {
                    content.classList.add('active');
                }
            });
        });
    });

    // --- EML Upload Drag & Drop Logic ---
    dragDropZone.addEventListener('dragenter', (e) => {
        e.preventDefault();
        dragDropZone.classList.add('dragover');
    });

    dragDropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dragDropZone.classList.add('dragover');
    });

    dragDropZone.addEventListener('dragleave', () => {
        dragDropZone.classList.remove('dragover');
    });

    dragDropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dragDropZone.classList.remove('dragover');
        
        if (e.dataTransfer.files.length > 0) {
            handleFileSelect(e.dataTransfer.files[0]);
        }
    });

    emlFileInput.addEventListener('change', () => {
        if (emlFileInput.files.length > 0) {
            handleFileSelect(emlFileInput.files[0]);
        }
    });

    function handleFileSelect(file) {
        if (!file.name.endsWith('.eml')) {
            alert('Please select a valid .eml file.');
            return;
        }
        selectedEmlFile = file;
        selectedFileName.style.display = 'flex';
        selectedFileName.querySelector('span').textContent = `${file.name} (${formatBytes(file.size)})`;
        uploadSubmitBtn.removeAttribute('disabled');
    }

    // --- IMAP Preset Autofill ---
    imapPreset.addEventListener('change', () => {
        const val = imapPreset.value;
        if (val === 'custom') {
            imapHost.value = '';
            imapPort.value = '993';
            imapHost.removeAttribute('readonly');
        } else {
            imapHost.value = val;
            imapPort.value = '993';
            imapHost.setAttribute('readonly', true);
        }
    });

    // --- Scan State Transition Ticker ---
    function triggerScanAnimation(logs, completeCallback) {
        resultsIdle.style.display = 'none';
        resultsComplete.style.display = 'none';
        resultsScanning.style.display = 'flex';
        scannerProgress.style.width = '0%';
        scanLogs.innerHTML = '';
        
        let currentIdx = 0;
        
        function runNextStep() {
            if (currentIdx >= logs.length) {
                completeCallback();
                return;
            }
            
            const log = logs[currentIdx];
            scannerStatus.textContent = log.title;
            scannerProgress.style.width = `${((currentIdx + 1) / logs.length) * 100}%`;
            
            // Mark previous as done
            const items = scanLogs.querySelectorAll('.scan-log-item');
            if (items.length > 0) {
                const prev = items[items.length - 1];
                prev.classList.remove('active');
                prev.innerHTML = `<i class="fa-solid fa-circle-check" style="color: var(--color-safe);"></i> ${prev.getAttribute('data-text')} // DONE`;
            }
            
            // Add new active log
            const logItem = document.createElement('div');
            logItem.className = 'scan-log-item active';
            logItem.setAttribute('data-text', log.desc);
            logItem.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> ${log.desc}...`;
            scanLogs.appendChild(logItem);
            scanLogs.scrollTop = scanLogs.scrollHeight;
            
            currentIdx++;
            setTimeout(runNextStep, log.duration);
        }
        
        runNextStep();
    }

    // --- Form Submissions ---

    // 1. Plain Text Manual Scan
    pasteForm.addEventListener('submit', (e) => {
        e.preventDefault();
        
        const payload = {
            body: document.getElementById('email-body').value,
            from_header: document.getElementById('from-header').value,
            subject: document.getElementById('subject-header').value || 'Manual Text Scan',
            gemini_key: geminiKeyInput.value
        };

        const scanSteps = [
            { title: 'Deconstructing Text', desc: 'Decoding raw input fields', duration: 400 },
            { title: 'Sender Investigation', desc: 'Evaluating headers and looking for spoofed display names', duration: 600 },
            { title: 'Deep URL Extraction', desc: 'Parsing anchor tags and text link arrays', duration: 500 },
            { title: 'NLP Urgency Classification', desc: 'Scanning threat lexicon and sentence pressure indicators', duration: 700 },
            { title: 'Compiling Report', desc: 'Finalizing heuristics and requesting AI summary', duration: 600 }
        ];

        triggerScanAnimation(scanSteps, () => {
            fetch('/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            .then(res => res.json())
            .then(data => {
                if (data.error) throw new Error(data.error);
                renderResults(data);
            })
            .catch(err => {
                showErrorState(err.message);
            });
        });
    });

    // 2. EML File Scan
    uploadSubmitBtn.addEventListener('click', () => {
        if (!selectedEmlFile) return;

        const formData = new FormData();
        formData.append('email_file', selectedEmlFile);
        formData.append('gemini_key', geminiKeyInput.value);

        const scanSteps = [
            { title: 'Unpacking EML', desc: 'Reading raw MIME stream and headers', duration: 500 },
            { title: 'Extracting Boundaries', desc: 'Separating text body, HTML code, and raw boundary elements', duration: 400 },
            { title: 'DKIM/Sender Validation', desc: 'Parsing sender credentials and running typosquatting tests', duration: 600 },
            { title: 'Link Deconstruction', desc: 'Resolving nested HTML hrefs and extracting redirect structures', duration: 600 },
            { title: 'Attachment Checksum Filter', desc: 'Scanning attachment filenames and risk extension models', duration: 500 },
            { title: 'Language Model Parsing', desc: 'Applying lexical urgency check and generating AI report', duration: 800 }
        ];

        triggerScanAnimation(scanSteps, () => {
            fetch('/analyze', {
                method: 'POST',
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                if (data.error) throw new Error(data.error);
                renderResults(data);
            })
            .catch(err => {
                showErrorState(err.message);
            });
        });
    });

    // 3. IMAP Connection Submit
    imapLoginForm.addEventListener('submit', (e) => {
        e.preventDefault();
        
        const host = imapHost.value;
        const port = imapPort.value;
        const emailVal = imapEmail.value;
        const password = imapPassword.value;

        imapCredentials = { host, port, email: emailVal, password };

        // Disable button, show connecting spinner
        const connectBtn = document.getElementById('imap-connect-btn');
        const origContent = connectBtn.innerHTML;
        connectBtn.setAttribute('disabled', true);
        connectBtn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Contacting Mailbox Server...`;

        fetch('/imap/connect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ host, port, email: emailVal, password })
        })
        .then(res => res.json())
        .then(data => {
            connectBtn.innerHTML = origContent;
            connectBtn.removeAttribute('disabled');

            if (data.error) throw new Error(data.error);

            // Success: Hide form, show mail list table
            imapLoginForm.style.display = 'none';
            imapMailListContainer.style.display = 'block';
            
            // Populate emails table
            imapEmailsBody.innerHTML = '';
            if (data.emails.length === 0) {
                imapEmailsBody.innerHTML = `<tr><td colspan="4" class="text-center">No emails found in INBOX.</td></tr>`;
            } else {
                data.emails.forEach(mail => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${formatDate(mail.date)}</td>
                        <td><span class="sender-name">${escapeHtml(mail.sender)}</span></td>
                        <td><span class="subject-txt">${escapeHtml(mail.subject)}</span></td>
                        <td>
                            <button class="scan-mini-btn" data-uid="${mail.uid}">
                                <i class="fa-solid fa-magnifying-glass"></i> Analyze
                            </button>
                        </td>
                    `;
                    
                    // Attach click handler to rows or buttons
                    tr.querySelector('.scan-mini-btn').addEventListener('click', (ev) => {
                        ev.stopPropagation();
                        fetchAndScanImapMail(mail.uid);
                    });
                    
                    imapEmailsBody.appendChild(tr);
                });
            }
        })
        .catch(err => {
            connectBtn.innerHTML = origContent;
            connectBtn.removeAttribute('disabled');
            
            const errMsg = err.message;
            if (errMsg.includes('Application-specific password required') || errMsg.includes('application-specific password')) {
                alert(
                    "Google App Password Required:\n\n" +
                    "Google does not allow third-party apps to log in with your primary account password when 2-Step Verification is enabled. You must use an App Password.\n\n" +
                    "How to generate a Google App Password:\n" +
                    "1. Go to your Google Account (myaccount.google.com)\n" +
                    "2. Navigate to the 'Security' tab on the left menu\n" +
                    "3. Under 'How you sign in to Google', select '2-Step Verification' (make sure it is active)\n" +
                    "4. Scroll to the very bottom and select 'App passwords'\n" +
                    "5. Give it a name (e.g. 'SentryMail') and click 'Create'\n" +
                    "6. Copy the generated 16-character password (e.g. 'abcd efgh ijkl mnop') and use it in the password box here instead of your Gmail password."
                );
            } else {
                alert(`IMAP Connection Failed: ${errMsg}`);
            }
        });
    });

    // IMAP Disconnect
    imapDisconnectBtn.addEventListener('click', () => {
        imapCredentials = null;
        imapMailListContainer.style.display = 'none';
        imapLoginForm.style.display = 'grid';
        imapLoginForm.reset();
    });

    function fetchAndScanImapMail(uid) {
        if (!imapCredentials) return;

        const payload = {
            ...imapCredentials,
            uid,
            gemini_key: geminiKeyInput.value
        };

        const scanSteps = [
            { title: 'Accessing Mailbox', desc: 'Securely authenticating and opening connection', duration: 400 },
            { title: 'Downloading Email Body', desc: 'Fetching full message body stream via UID', duration: 500 },
            { title: 'Decoding MIME Parts', desc: 'Deconstructing text and file layers', duration: 500 },
            { title: 'Reputation Lookup', desc: 'Checking sender domains and lookalike names', duration: 600 },
            { title: 'Scanning Links', desc: 'Evaluating nested hyperlinks and target protocols', duration: 600 },
            { title: 'Attachment Audit', desc: 'Filtering file payloads and extensions', duration: 400 },
            { title: 'Gemini NLP Assessment', desc: 'Evaluating email urgency factors and calling AI explainer', duration: 800 }
        ];

        triggerScanAnimation(scanSteps, () => {
            fetch('/imap/fetch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            .then(res => res.json())
            .then(data => {
                if (data.error) throw new Error(data.error);
                renderResults(data);
            })
            .catch(err => {
                showErrorState(err.message);
            });
        });
    }

    // --- Render Results ---
    function renderResults(data) {
        const details = data.email_details;
        const analysis = data.analysis;

        // Hide scanning, show complete
        resultsScanning.style.display = 'none';
        resultsComplete.style.display = 'flex';
        
        // --- 1. Score & Threat Meter Arc Animation ---
        const score = analysis.final_score;
        resultScoreVal.textContent = score;
        
        // Gauge Arc Perimeter = 125.6 (semi circle with r=40)
        const offset = 125.6 - (score / 100) * 125.6;
        gaugeFillArc.style.strokeDashoffset = offset;
        
        // Clear classes and assign threat levels
        gaugeFillArc.classList.remove('gauge-safe', 'gauge-caution', 'gauge-danger');
        resultThreatBadge.className = 'gauge-threat-label';
        
        if (analysis.overall_threat === 'Danger') {
            gaugeFillArc.classList.add('gauge-danger');
            resultThreatBadge.classList.add('threat-danger');
            resultThreatBadge.textContent = 'Danger';
            resultsPanel.style.border = '1px solid rgba(239, 68, 68, 0.2)';
        } else if (analysis.overall_threat === 'Caution') {
            gaugeFillArc.classList.add('gauge-caution');
            resultThreatBadge.classList.add('threat-caution');
            resultThreatBadge.textContent = 'Caution';
            resultsPanel.style.border = '1px solid rgba(245, 158, 11, 0.2)';
        } else {
            gaugeFillArc.classList.add('gauge-safe');
            resultThreatBadge.classList.add('threat-safe');
            resultThreatBadge.textContent = 'Safe';
            resultsPanel.style.border = '1px solid rgba(16, 185, 129, 0.2)';
        }

        // --- 2. Meta Details ---
        resultMetaSubject.textContent = details.subject;
        resultMetaSender.textContent = details.sender;
        resultMetaDate.textContent = details.date;

        // --- 3. AI Explanation ---
        // Basic Markdown-to-HTML parser for basic formatting (bold and bullets)
        resultAiExplanation.innerHTML = formatMarkdown(analysis.explanation);

        // --- 4. Sub-Module Score Badges ---
        updateModuleBadge(badgeSender, analysis.modules.sender.threat_level);
        updateModuleBadge(badgeLinks, analysis.modules.links.threat_level);
        updateModuleBadge(badgeUrgency, analysis.modules.nlp.threat_level);
        updateModuleBadge(badgeAttachments, analysis.modules.attachments.threat_level);

        // --- 5. Populate Modules Contents ---

        // A. SENDER
        senderDetailsContainer.innerHTML = '';
        const senderInfo = analysis.modules.sender;
        
        // Create Sender item card
        const senderCard = document.createElement('div');
        senderCard.className = `detail-item ${senderInfo.threat_level.toLowerCase()}`;
        senderCard.innerHTML = `
            <div class="detail-title">
                <span>Sender Domain Reputation</span>
                <span>Threat: ${senderInfo.threat_level}</span>
            </div>
            <div class="detail-desc">
                <p><strong>Parsed Name:</strong> ${escapeHtml(senderInfo.sender_name || 'N/A')}</p>
                <p><strong>Parsed Email:</strong> ${escapeHtml(senderInfo.sender_email)}</p>
                <p><strong>Domain:</strong> ${escapeHtml(senderInfo.sender_domain)}</p>
            </div>
            <div class="sender-checks-bullets" style="margin-top: 10px;">
                ${senderInfo.findings.map(f => `
                    <div class="warning-bullet ${senderInfo.threat_level.toLowerCase()}">
                        <i class="fa-solid fa-triangle-exclamation"></i>
                        <span>${f}</span>
                    </div>
                `).join('')}
                ${senderInfo.findings.length === 0 ? `
                    <div class="warning-bullet safe">
                        <i class="fa-solid fa-circle-check" style="color: var(--color-safe);"></i>
                        <span>Sender domain appears valid and no typosquatting detected.</span>
                    </div>
                ` : ''}
            </div>
        `;
        senderDetailsContainer.appendChild(senderCard);

        // B. LINKS
        linksDetailsContainer.innerHTML = '';
        const linksInfo = analysis.modules.links;
        if (linksInfo.extracted_links.length === 0) {
            linksDetailsContainer.innerHTML = `
                <div class="empty-details-notice">
                    <i class="fa-solid fa-link-slash"></i>
                    <p>No links/URLs were detected in the email body.</p>
                </div>`;
        } else {
            linksInfo.extracted_links.forEach(l => {
                const linkCard = document.createElement('div');
                linkCard.className = `detail-item ${l.is_suspicious ? 'danger' : 'safe'}`;
                
                // Find matching warnings if suspicious
                const warningObj = linksInfo.findings.find(f => f.url === l.url);
                const warningsHtml = warningObj 
                    ? warningObj.warnings.map(w => `
                        <div class="warning-bullet danger">
                            <i class="fa-solid fa-circle-exclamation"></i>
                            <span>${w}</span>
                        </div>`).join('') 
                    : `<div class="warning-bullet safe">
                        <i class="fa-solid fa-circle-check" style="color: var(--color-safe);"></i>
                        <span>Link analysis found no suspicious features.</span>
                       </div>`;

                linkCard.innerHTML = `
                    <div class="detail-title" style="word-break: break-all;">
                        <span>Link: ${escapeHtml(l.url)}</span>
                        <span>${l.is_suspicious ? 'Flagged' : 'Clean'}</span>
                    </div>
                    <div class="detail-desc">
                        <p><strong>Anchor Text:</strong> ${escapeHtml(l.anchor_text || '(None / Image link)')}</p>
                        <div style="margin-top: 6px;">${warningsHtml}</div>
                    </div>
                `;
                linksDetailsContainer.appendChild(linkCard);
            });
        }

        // C. URGENCY
        const nlpInfo = analysis.modules.nlp;
        nlpMetricUrgency.textContent = nlpInfo.metrics.urgency_matches;
        nlpMetricCredentials.textContent = nlpInfo.metrics.security_matches;
        nlpMetricFinancial.textContent = nlpInfo.metrics.financial_matches;

        urgencyDetailsContainer.innerHTML = '';
        if (nlpInfo.findings.length === 0) {
            urgencyDetailsContainer.innerHTML = `
                <div class="empty-details-notice">
                    <i class="fa-solid fa-message"></i>
                    <p>No urgent or high-pressure language patterns detected.</p>
                </div>`;
        } else {
            nlpInfo.findings.forEach(s => {
                const sentenceCard = document.createElement('div');
                sentenceCard.className = 'detail-item caution';
                sentenceCard.innerHTML = `
                    <div class="detail-title">
                        <span>Triggered Phrase Detection</span>
                        <span>Tone: Urgent</span>
                    </div>
                    <div class="detail-desc">
                        <p style="font-style: italic; color: #fff;">"${escapeHtml(s.text)}"</p>
                        <p style="margin-top: 6px; font-size: 0.74rem;"><strong>Triggers:</strong> ${s.triggers.map(t => `<span style="background: rgba(245,158,11,0.15); color: var(--color-caution); padding: 2px 6px; border-radius: 4px; font-family: var(--font-code); margin-right: 4px;">${t}</span>`).join('')}</p>
                    </div>
                `;
                urgencyDetailsContainer.appendChild(sentenceCard);
            });
        }

        // D. ATTACHMENTS
        attachmentsDetailsContainer.innerHTML = '';
        const attachmentsInfo = analysis.modules.attachments;
        if (details.attachments.length === 0) {
            attachmentsDetailsContainer.innerHTML = `
                <div class="empty-details-notice">
                    <i class="fa-solid fa-paperclip"></i>
                    <p>No file attachments detected in this email.</p>
                </div>`;
        } else {
            details.attachments.forEach(att => {
                const attCard = document.createElement('div');
                // Check if flagged
                const flaggedObj = attachmentsInfo.findings.find(f => f.filename === att.filename);
                const isFlagged = !!flaggedObj;
                
                attCard.className = `detail-item ${isFlagged ? (flaggedObj.risk === 'High' ? 'danger' : 'caution') : 'safe'}`;
                
                const warningsHtml = isFlagged 
                    ? flaggedObj.warnings.map(w => `
                        <div class="warning-bullet ${flaggedObj.risk === 'High' ? 'danger' : 'caution'}">
                            <i class="fa-solid fa-triangle-exclamation"></i>
                            <span>${w}</span>
                        </div>`).join('') 
                    : `<div class="warning-bullet safe">
                        <i class="fa-solid fa-circle-check" style="color: var(--color-safe);"></i>
                        <span>Safe extension detected.</span>
                       </div>`;

                attCard.innerHTML = `
                    <div class="detail-title">
                        <span><i class="fa-solid fa-file"></i> ${escapeHtml(att.filename)}</span>
                        <span>${isFlagged ? flaggedObj.risk + ' Risk' : 'Safe'}</span>
                    </div>
                    <div class="detail-desc">
                        <p><strong>Size:</strong> ${formatBytes(att.size)} // <strong>MIME type:</strong> ${escapeHtml(att.content_type || 'Unknown')}</p>
                        <div style="margin-top: 6px;">${warningsHtml}</div>
                    </div>
                `;
                attachmentsDetailsContainer.appendChild(attCard);
            });
        }

        // --- 6. Email Content Viewer Injection ---
        emailRawTextContent.textContent = details.body;
        
        // Write HTML code to Iframe
        if (details.html_content) {
            emailHtmlIframe.style.display = 'block';
            // Enable visual template inside sandboxed iframe
            const doc = emailHtmlIframe.contentDocument || emailHtmlIframe.contentWindow.document;
            doc.open();
            doc.write(details.html_content);
            doc.close();
            
            // Show the HTML tab button
            document.querySelector('[data-view="view-html"]').style.display = 'inline-block';
        } else {
            // No HTML: hide tab button, default to text view
            document.querySelector('[data-view="view-html"]').style.display = 'none';
            triggerViewTab('view-text');
        }
    }

    // --- Reset Scan to Idle state ---
    resetScanBtn.addEventListener('click', () => {
        resultsComplete.style.display = 'none';
        resultsPanel.style.border = '1px solid var(--border-color)';
        
        if (imapCredentials && imapMailListContainer.style.display === 'block') {
            // If scanning IMAP mailbox, return to mailbox view
            resultsIdle.style.display = 'flex';
        } else {
            // General reset
            resultsIdle.style.display = 'flex';
            pasteForm.reset();
            selectedEmlFile = null;
            selectedFileName.style.display = 'none';
            uploadSubmitBtn.setAttribute('disabled', true);
        }
    });

    // --- Details tab toggling logic ---
    modTabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetMod = btn.getAttribute('data-mod');
            modTabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            modContents.forEach(c => {
                c.classList.remove('active');
                if (c.id === targetMod) c.classList.add('active');
            });
        });
    });

    // --- Viewer tab toggling logic ---
    viewTabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetView = btn.getAttribute('data-view');
            triggerViewTab(targetView);
        });
    });

    function triggerViewTab(viewId) {
        viewTabBtns.forEach(b => {
            b.classList.remove('active');
            if (b.getAttribute('data-view') === viewId) b.classList.add('active');
        });

        viewContents.forEach(c => {
            c.classList.remove('active');
            if (c.id === viewId) c.classList.add('active');
        });
    }

    function updateModuleBadge(badgeEl, threatLevel) {
        badgeEl.className = 'badge';
        if (threatLevel === 'Danger') {
            badgeEl.classList.add('danger');
            badgeEl.innerHTML = `<i class="fa-solid fa-circle-xmark"></i>`;
        } else if (threatLevel === 'Caution') {
            badgeEl.classList.add('caution');
            badgeEl.innerHTML = `<i class="fa-solid fa-circle-exclamation"></i>`;
        } else {
            badgeEl.classList.add('safe');
            badgeEl.innerHTML = `<i class="fa-solid fa-circle-check"></i>`;
        }
    }

    function showErrorState(message) {
        resultsScanning.style.display = 'none';
        resultsIdle.style.display = 'flex';
        alert(`Analysis Error: ${message}`);
    }

    // --- Helper Formatting Utilities ---
    function formatBytes(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    function formatDate(dateStr) {
        if (!dateStr) return 'N/A';
        try {
            const parsed = new Date(dateStr);
            if (isNaN(parsed.getTime())) return dateStr;
            return parsed.toLocaleDateString(undefined, {month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'});
        } catch {
            return dateStr;
        }
    }

    function escapeHtml(text) {
        if (!text) return '';
        const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
        return text.toString().replace(/[&<>"']/g, m => map[m]);
    }

    function formatMarkdown(text) {
        if (!text) return '';
        // Escape HTML first to prevent raw script injections
        let html = escapeHtml(text);
        
        // Replace bold tags: **text** -> <strong>text</strong>
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Bullet list lines: - text or * text
        html = html.replace(/^(?:-|\*)\s+(.*?)$/gm, '<li>$1</li>');
        
        // Wrap <li> groups in <ul>
        // Match contiguous <li> groups
        html = html.replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>');
        
        // Newlines to line breaks (outside lists)
        html = html.replace(/\n/g, '<br>');
        
        return html;
    }
});
