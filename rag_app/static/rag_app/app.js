document.addEventListener('DOMContentLoaded', () => {
    // UI Elements
    const btnIngest = document.getElementById('btn-ingest');
    const inputRepoPath = document.getElementById('repo-path');
    const msgIngestStatus = document.getElementById('ingest-status-msg');
    
    const badgeDbStatus = document.getElementById('db-status-badge');
    const textChunkCount = document.getElementById('chunk-count');
    const textBgTaskStatus = document.getElementById('bg-task-status');
    const btnRefreshStatus = document.getElementById('btn-refresh-status');
    
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');
    const btnSend = document.getElementById('btn-send');
    const btnExplainCode = document.getElementById('btn-explain-code');
    const btnClearChat = document.getElementById('btn-clear-chat');

    // --- Theme Toggle ---
    const themeToggle = document.getElementById('theme-toggle');
    
    if (themeToggle) {
        const iconMoon = themeToggle.querySelector('.icon-moon');
        const iconSun = themeToggle.querySelector('.icon-sun');

        // Check initialized preference
        if (localStorage.getItem('theme') === 'dark' || (!localStorage.getItem('theme') && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            document.documentElement.setAttribute('data-theme', 'dark');
            iconMoon.classList.add('hidden');
            iconSun.classList.remove('hidden');
        }

        themeToggle.addEventListener('click', () => {
            let currentTheme = document.documentElement.getAttribute('data-theme');
            let newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            
            if (newTheme === 'dark') {
                iconMoon.classList.add('hidden');
                iconSun.classList.remove('hidden');
            } else {
                iconSun.classList.add('hidden');
                iconMoon.classList.remove('hidden');
            }
        });
    }

    // Auto-resize textarea
    chatInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
        if (this.value.trim() === '') {
            btnSend.disabled = true;
            btnExplainCode.disabled = true;
        } else {
            btnSend.disabled = false;
            btnExplainCode.disabled = false;
        }
    });

    chatInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (this.value.trim() !== '') {
                btnSend.click();
            }
        }
    });

    // (Theme Toggle logic removed from outer scope and placed inside DOMContentLoaded below)

    // Configure marked wrapper for safe HTML rendering and syntax highlighting
    marked.setOptions({
        gfm: true,
        breaks: true,
        highlight: function(code, lang) {
            const language = hljs.getLanguage(lang) ? lang : 'plaintext';
            return hljs.highlight(code, { language }).value;
        }
    });

    // --- Quick Prompts ---
    document.querySelectorAll('.quick-prompt').forEach(button => {
        button.addEventListener('click', () => {
            chatInput.value = button.getAttribute('data-prompt');
            chatInput.dispatchEvent(new Event('input')); // trigger resize and button enable
            chatInput.focus();
        });
    });

    // --- State Polling ---
    let statusInterval = null;

    async function fetchSystemStatus() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            
            updateStatusUI(data);
            
            if (data.indexing_status && data.indexing_status.is_indexing) {
                if (!statusInterval) {
                    statusInterval = setInterval(fetchSystemStatus, 2000);
                }
            } else {
                if (statusInterval) {
                    clearInterval(statusInterval);
                    statusInterval = null;
                }
                
                if (data.indexing_status && data.indexing_status.last_success) {
                    if (!msgIngestStatus.innerText.includes("successfully")) {
                        showIngestStatus("Indexing finished successfully.", "success");
                    }
                } else if (data.indexing_status && data.indexing_status.last_error) {
                    showIngestStatus(`Error: ${data.indexing_status.last_error}`, "error");
                }
            }
        } catch (error) {
            console.error("Failed to fetch status:", error);
            textBgTaskStatus.innerText = "Error fetching status";
            textBgTaskStatus.style.color = "var(--error)";
        }
    }

    function updateStatusUI(data) {
        const cnt = data.database_stats.document_chunks || 0;
        
        // Animate counter
        const currentCnt = parseInt(textChunkCount.innerText.replace(/,/g, '')) || 0;
        if (currentCnt !== cnt) {
            animateValue(textChunkCount, currentCnt, cnt, 1000);
        }
        
        if (cnt > 0) {
            badgeDbStatus.className = "badge success";
            badgeDbStatus.innerText = "Online";
        } else {
            badgeDbStatus.className = "badge warning";
            badgeDbStatus.innerText = "Empty";
        }
        
        if (data.indexing_status && data.indexing_status.is_indexing) {
            textBgTaskStatus.innerText = "Indexing Project...";
            textBgTaskStatus.style.color = "var(--warning)";
            btnIngest.disabled = true;
            btnIngest.querySelector('span').innerText = "Processing...";
        } else {
            textBgTaskStatus.innerText = "Idle";
            textBgTaskStatus.style.color = "var(--text-primary)";
            btnIngest.disabled = false;
            btnIngest.querySelector('span').innerText = "Index Codebase";
        }
    }

    function animateValue(obj, start, end, duration) {
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            obj.innerHTML = Math.floor(progress * (end - start) + start).toLocaleString();
            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
        };
        window.requestAnimationFrame(step);
    }

    function showIngestStatus(msg, type = 'info') {
        msgIngestStatus.innerText = msg;
        msgIngestStatus.className = 'status-message';
        msgIngestStatus.classList.remove('hidden');
        
        if (type === 'error') {
            msgIngestStatus.style.borderColor = 'var(--error)';
            msgIngestStatus.style.color = 'var(--error)';
        } else if (type === 'success') {
            msgIngestStatus.style.borderColor = 'var(--success)';
            msgIngestStatus.style.color = 'var(--success)';
        } else {
            msgIngestStatus.style.borderColor = 'var(--accent)';
            msgIngestStatus.style.color = 'var(--text-primary)';
        }
    }

    // --- Actions ---

    btnRefreshStatus.addEventListener('click', () => {
        const icon = btnRefreshStatus.querySelector('svg');
        icon.style.animation = 'spin 1s linear';
        fetchSystemStatus().then(() => {
            setTimeout(() => icon.style.animation = '', 1000);
        });
    });

    btnIngest.addEventListener('click', async () => {
        const path = inputRepoPath.value.trim();
        if (!path) {
            showIngestStatus("Please provide a repository path first.", "warning");
            return;
        }
        
        btnIngest.disabled = true;
        showIngestStatus("Preparing ingestion task...", "info");
        
        try {
            const response = await fetch('/api/ingest', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: path })
            });
            
            const data = await response.json();
            if (response.ok) {
                showIngestStatus("Indexing job started! Background task running.");
                fetchSystemStatus(); // Start polling
            } else {
                showIngestStatus(data.detail || "Failed to start ingestion.", "error");
                btnIngest.disabled = false;
            }
        } catch (error) {
            showIngestStatus("Network error submitting request.", "error");
            btnIngest.disabled = false;
        }
    });

    // --- Chat Interface ---

    function appendUserMessage(text) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message user';
        msgDiv.innerHTML = `
            <div class="avatar">
                <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
            </div>
            <div class="message-content">
                <p>${text.replace(/</g, "&lt;").replace(/>/g, "&gt;")}</p>
            </div>
        `;
        chatMessages.appendChild(msgDiv);
        scrollToBottom();
    }

    function showTypingIndicator() {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message assistant typing-wrapper';
        msgDiv.id = 'typing-indicator';
        msgDiv.innerHTML = `
            <div class="avatar assistant-avatar">
                <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"></path><rect x="4" y="8" width="16" height="12" rx="2"></rect><path d="M2 14h2"></path><path d="M20 14h2"></path><path d="M15 13v2"></path><path d="M9 13v2"></path></svg>
            </div>
            <div class="message-content">
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;
        chatMessages.appendChild(msgDiv);
        scrollToBottom();
    }

    function removeTypingIndicator() {
        const el = document.getElementById('typing-indicator');
        if (el) el.remove();
    }

    function wrapCodeBlocksWithCopy(htmlString) {
        // Create a temporary DOM element to parse and manipulate HTML
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = htmlString;
        
        // Find all pre elements
        const preElements = tempDiv.querySelectorAll('pre');
        
        preElements.forEach(pre => {
            const codeEl = pre.querySelector('code');
            let lang = 'code';
            if (codeEl && codeEl.className) {
                const match = codeEl.className.match(/language-(\w+)/);
                if (match) lang = match[1];
            }
            
            // Normal Code wrapping (w/ Copy button)
            const wrapper = document.createElement('div');
            wrapper.className = 'code-block-wrapper';
            
            const header = document.createElement('div');
            header.className = 'code-header';
            header.innerHTML = `
                <span class="lang-label">${lang}</span>
                <button class="copy-btn">
                    <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2" fill="none"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                    Copy code
                </button>
            `;
            
            pre.parentNode.insertBefore(wrapper, pre);
            wrapper.appendChild(header);
            wrapper.appendChild(pre);
            
            const copyBtn = header.querySelector('.copy-btn');
            copyBtn.addEventListener('click', () => {
                const codeText = pre.innerText;
                navigator.clipboard.writeText(codeText).then(() => {
                    const originalHTML = copyBtn.innerHTML;
                    copyBtn.innerHTML = `<svg viewBox="0 0 24 24" width="14" height="14" stroke="var(--success)" stroke-width="2" fill="none"><polyline points="20 6 9 17 4 12"></polyline></svg> Copied!`;
                    copyBtn.style.color = 'var(--success)';
                    setTimeout(() => {
                        copyBtn.innerHTML = originalHTML;
                        copyBtn.style.color = '';
                    }, 2000);
                });
            });
        });
        
        return tempDiv.innerHTML;
    }

    function appendAssistantMessage(markdownText) {
        removeTypingIndicator();
        
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message assistant';
        
        // Parse Markdown
        let htmlContent = marked.parse(markdownText);
        
        // Enhance code blocks with headers and copy buttons
        htmlContent = wrapCodeBlocksWithCopy(htmlContent);
        
        msgDiv.innerHTML = `
            <div class="avatar assistant-avatar">
                <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"></path><rect x="4" y="8" width="16" height="12" rx="2"></rect><path d="M2 14h2"></path><path d="M20 14h2"></path><path d="M15 13v2"></path><path d="M9 13v2"></path></svg>
            </div>
            <div class="message-content">
                ${htmlContent}
                <div class="message-actions" style="margin-top: 10px; text-align: right;">
                    <button class="copy-answer-btn btn-secondary" style="display: inline-flex; font-size: 0.75rem; padding: 4px 8px; border-radius: 4px;" data-raw="${encodeURIComponent(markdownText)}">
                        <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2" fill="none"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg> Copy Answer
                    </button>
                </div>
            </div>
        `;
        chatMessages.appendChild(msgDiv);
        
        // Add Copy Answer listener
        const copyBtn = msgDiv.querySelector('.copy-answer-btn');
        if (copyBtn) {
            copyBtn.addEventListener('click', function() {
                const rawText = decodeURIComponent(this.getAttribute('data-raw'));
                navigator.clipboard.writeText(rawText).then(() => {
                    const originalHTML = this.innerHTML;
                    this.innerHTML = `<svg viewBox="0 0 24 24" width="14" height="14" stroke="var(--success)" stroke-width="2" fill="none"><polyline points="20 6 9 17 4 12"></polyline></svg> Copied!`;
                    this.style.color = 'var(--success)';
                    this.style.borderColor = 'var(--success)';
                    setTimeout(() => {
                        this.innerHTML = originalHTML;
                        this.style.color = '';
                        this.style.borderColor = '';
                    }, 2000);
                });
            });
        }
        

        scrollToBottom();
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const question = chatInput.value.trim();
        if (!question) return;
        
        // Hide welcome message if it's there
        const welcome = document.querySelector('.welcome-message');
        if (welcome) welcome.style.display = 'none';
        
        chatInput.value = '';
        chatInput.style.height = 'auto';
        btnSend.disabled = true;
        
        appendUserMessage(question);
        showTypingIndicator();
        
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: question })
            });
            
            if (response.ok) {
                const contentType = response.headers.get("content-type");
                if (contentType && contentType.includes("application/json")) {
                    const data = await response.json();
                    appendAssistantMessage(data.answer || data.detail);
                } else {
                    // Streaming response
                    removeTypingIndicator();
                    
                    const msgDiv = document.createElement('div');
                    msgDiv.className = 'message assistant';
                    msgDiv.innerHTML = `
                        <div class="avatar assistant-avatar">
                            <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"></path><rect x="4" y="8" width="16" height="12" rx="2"></rect><path d="M2 14h2"></path><path d="M20 14h2"></path><path d="M15 13v2"></path><path d="M9 13v2"></path></svg>
                        </div>
                        <div class="message-content"></div>
                    `;
                    chatMessages.appendChild(msgDiv);
                    const contentDiv = msgDiv.querySelector('.message-content');
                    
                    const reader = response.body.getReader();
                    const decoder = new TextDecoder('utf-8');
                    let aiText = "";
                    
                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) break;
                        
                        aiText += decoder.decode(value, { stream: true });
                        let htmlContent = marked.parse(aiText);
                        htmlContent = wrapCodeBlocksWithCopy(htmlContent);
                        // For streaming, we append the copy button outline but don't bind it fully until done
                        contentDiv.innerHTML = htmlContent + `
                <div class="message-actions" style="margin-top: 10px; text-align: right;">
                    <button class="copy-answer-btn btn-secondary" style="display: inline-flex; font-size: 0.75rem; padding: 4px 8px; border-radius: 4px;" data-raw="${encodeURIComponent(aiText)}">
                        <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2" fill="none"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg> Copy Answer
                    </button>
                </div>
                        `;
                        scrollToBottom();
                        
                        // Re-bind listener
                        const copyBtn = msgDiv.querySelector('.copy-answer-btn');
                        if (copyBtn) {
                            copyBtn.addEventListener('click', function() {
                                const rawText = decodeURIComponent(this.getAttribute('data-raw'));
                                navigator.clipboard.writeText(rawText).then(() => {
                                    const originalHTML = this.innerHTML;
                                    this.innerHTML = `<svg viewBox="0 0 24 24" width="14" height="14" stroke="var(--success)" stroke-width="2" fill="none"><polyline points="20 6 9 17 4 12"></polyline></svg> Copied!`;
                                    setTimeout(() => { this.innerHTML = originalHTML; }, 2000);
                                });
                            });
                        }
                    }
                    
                }
            } else {
                const data = await response.json().catch(() => ({}));
                appendAssistantMessage(`**Error:** ${data.detail || "Failed to get response"}`);
            }
        } catch (error) {
            appendAssistantMessage(`**Connection Error:** Could not reach the API. Is your server running?`);
        }
    });

    // Handle Explain Code
    btnExplainCode.addEventListener('click', async () => {
        const code = chatInput.value.trim();
        if (!code) return;
        
        const welcome = document.querySelector('.welcome-message');
        if (welcome) welcome.style.display = 'none';
        
        chatInput.value = '';
        chatInput.style.height = 'auto';
        btnSend.disabled = true;
        btnExplainCode.disabled = true;
        
        appendUserMessage("Explain this code:\\n```\\n" + code + "\\n```");
        showTypingIndicator();
        
        try {
            const response = await fetch('/api/explain-code', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code: code })
            });
            
            if (response.ok) {
                const contentType = response.headers.get("content-type");
                if (contentType && contentType.includes("application/json")) {
                    const data = await response.json();
                    appendAssistantMessage(data.answer || data.detail);
                } else {
                    // Streaming response
                    removeTypingIndicator();
                    
                    const msgDiv = document.createElement('div');
                    msgDiv.className = 'message assistant';
                    msgDiv.innerHTML = `
                        <div class="avatar assistant-avatar">
                            <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"></path><rect x="4" y="8" width="16" height="12" rx="2"></rect><path d="M2 14h2"></path><path d="M20 14h2"></path><path d="M15 13v2"></path><path d="M9 13v2"></path></svg>
                        </div>
                        <div class="message-content"></div>
                    `;
                    chatMessages.appendChild(msgDiv);
                    const contentDiv = msgDiv.querySelector('.message-content');
                    
                    const reader = response.body.getReader();
                    const decoder = new TextDecoder('utf-8');
                    let aiText = "";
                    
                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) break;
                        
                        aiText += decoder.decode(value, { stream: true });
                        let htmlContent = marked.parse(aiText);
                        htmlContent = wrapCodeBlocksWithCopy(htmlContent);
                        contentDiv.innerHTML = htmlContent + `
                <div class="message-actions" style="margin-top: 10px; text-align: right;">
                    <button class="copy-answer-btn btn-secondary" style="display: inline-flex; font-size: 0.75rem; padding: 4px 8px; border-radius: 4px;" data-raw="${encodeURIComponent(aiText)}">
                        <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2" fill="none"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg> Copy Answer
                    </button>
                </div>
                        `;
                        scrollToBottom();
                        
                        // Re-bind listener
                        const copyBtn = msgDiv.querySelector('.copy-answer-btn');
                        if (copyBtn) {
                            copyBtn.addEventListener('click', function() {
                                const rawText = decodeURIComponent(this.getAttribute('data-raw'));
                                navigator.clipboard.writeText(rawText).then(() => {
                                    const originalHTML = this.innerHTML;
                                    this.innerHTML = `<svg viewBox="0 0 24 24" width="14" height="14" stroke="var(--success)" stroke-width="2" fill="none"><polyline points="20 6 9 17 4 12"></polyline></svg> Copied!`;
                                    setTimeout(() => { this.innerHTML = originalHTML; }, 2000);
                                });
                            });
                        }
                    }
                }
            } else {
                const data = await response.json().catch(() => ({}));
                appendAssistantMessage(`**Error:** ${data.detail || "Failed to get response"}`);
            }
        } catch (error) {
            appendAssistantMessage(`**Connection Error:** Could not reach the API. Is your server running?`);
        }
    });

    // Handle Clear Chat
    btnClearChat.addEventListener('click', () => {
        // Remove all messages except the welcome message if it existed
        const messages = chatMessages.querySelectorAll('.message:not(.welcome-message)');
        messages.forEach(msg => msg.remove());
        
        // Show welcome message again
        const welcome = document.querySelector('.welcome-message');
        if (welcome) welcome.style.display = 'flex';
    });

    // Add CSS block for the spin animation used in the refresh button
    if (!document.getElementById('dynamic-styles')) {
        const style = document.createElement('style');
        style.id = 'dynamic-styles';
        style.innerHTML = `@keyframes spin { 100% { transform: rotate(360deg); } }`;
        document.head.appendChild(style);
    }

    fetchSystemStatus();
});
