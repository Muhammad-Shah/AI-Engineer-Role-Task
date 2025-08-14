// Database Chatbot Frontend Application

class DatabaseChatbot {
    constructor() {
        this.apiBase = 'http://localhost:8000';
        this.connectionId = null;
        this.currentSessionId = null;
        this.sessions = [];
        this.isConnected = false;
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadSessions();
        this.updateUI();
        
        // Set initial database defaults
        const initialDbType = document.getElementById('db-type').value;
        this.updateConnectionDefaults(initialDbType);
    }

    bindEvents() {
        // Connection form
        document.getElementById('connection-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.connectDatabase();
        });

        // Disconnect button
        document.getElementById('disconnect-btn').addEventListener('click', () => {
            this.disconnectDatabase();
        });

        // Chat form
        document.getElementById('chat-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage();
        });

        // New session button
        document.getElementById('new-session-btn').addEventListener('click', () => {
            this.createNewSession();
        });

        // Clear chat button
        document.getElementById('clear-chat-btn').addEventListener('click', () => {
            this.clearChat();
        });

        // Export chat button
        document.getElementById('export-chat-btn').addEventListener('click', () => {
            this.exportChat();
        });

        // Example queries
        document.querySelectorAll('.example-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const query = e.target.getAttribute('data-query');
                document.getElementById('message-input').value = query;
                if (this.isConnected && this.currentSessionId) {
                    this.sendMessage();
                }
            });
        });

        // Database type change
        document.getElementById('db-type').addEventListener('change', (e) => {
            this.updateConnectionDefaults(e.target.value);
        });
    }

    updateConnectionDefaults(dbType) {
        const defaults = {
            postgresql: { port: 5432, username: 'postgres', password: 'postgres' },
            mysql: { port: 3306, username: 'root', password: 'password' },
            mongodb: { port: 27017, username: '', password: '' }
        };

        const config = defaults[dbType];
        if (config) {
            document.getElementById('port').value = config.port;
            document.getElementById('username').value = config.username;
            document.getElementById('password').value = config.password;
            
            // Update field requirements based on database type
            const usernameField = document.getElementById('username');
            const passwordField = document.getElementById('password');
            
            if (dbType === 'mongodb') {
                // For MongoDB, make fields optional (local development)
                usernameField.removeAttribute('required');
                passwordField.removeAttribute('required');
                usernameField.placeholder = 'Username (optional for local dev)';
                passwordField.placeholder = 'Password (optional for local dev)';
            } else {
                // For SQL databases, keep fields required
                usernameField.setAttribute('required', 'required');
                passwordField.setAttribute('required', 'required');
                usernameField.placeholder = 'Username';
                passwordField.placeholder = 'Password';
            }
        }
    }

    async connectDatabase() {
        const formData = new FormData(document.getElementById('connection-form'));
        const username = formData.get('username') || document.getElementById('username').value;
        const password = formData.get('password') || document.getElementById('password').value;
        const dbType = formData.get('db-type') || document.getElementById('db-type').value;
        
        const payload = {
            host: formData.get('host') || document.getElementById('host').value,
            port: parseInt(formData.get('port') || document.getElementById('port').value),
            database: formData.get('database') || document.getElementById('database').value,
            db_type: dbType
        };
        
        // Only include username/password if they have values
        if (username && username.trim()) {
            payload.username = username.trim();
        }
        if (password && password.trim()) {
            payload.password = password.trim();
        }

        this.showLoading(true);
        
        try {
            const response = await fetch(`${this.apiBase}/api/database/connect`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const result = await response.json();

            if (result.status === 'connected') {
                this.connectionId = result.connection_id;
                this.isConnected = true;
                this.updateConnectionInfo(result.database_info);
                this.showToast('Connected successfully!', 'success');
                this.updateUI();
            } else {
                this.showToast(`Connection failed: ${result.error || 'Unknown error'}`, 'error');
            }
        } catch (error) {
            this.showToast(`Connection error: ${error.message}`, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    async disconnectDatabase() {
        if (!this.connectionId) return;

        try {
            await fetch(`${this.apiBase}/api/database/disconnect/${this.connectionId}`, {
                method: 'DELETE'
            });

            this.connectionId = null;
            this.isConnected = false;
            this.updateUI();
            this.showToast('Disconnected successfully!', 'info');
        } catch (error) {
            this.showToast(`Disconnect error: ${error.message}`, 'error');
        }
    }

    updateConnectionInfo(dbInfo) {
        document.getElementById('connected-type').textContent = dbInfo.db_type;
        document.getElementById('connected-db').textContent = dbInfo.database;
        document.getElementById('connected-server').textContent = dbInfo.server_version || 'Unknown';
        document.getElementById('connection-info').classList.remove('hidden');
    }

    async createNewSession() {
        try {
            const response = await fetch(`${this.apiBase}/api/chat/sessions`, {
                method: 'POST'
            });

            const session = await response.json();
            this.currentSessionId = session.session_id;
            await this.loadSessions();
            this.selectSession(session.session_id);
            this.showToast('New session created!', 'success');
        } catch (error) {
            this.showToast(`Failed to create session: ${error.message}`, 'error');
        }
    }

    async loadSessions() {
        try {
            const response = await fetch(`${this.apiBase}/api/chat/sessions`);
            this.sessions = await response.json();
            this.renderSessions();
        } catch (error) {
            console.error('Failed to load sessions:', error);
        }
    }

    renderSessions() {
        const container = document.getElementById('sessions-list');
        
        if (this.sessions.length === 0) {
            container.innerHTML = '<p style="color: var(--text-secondary); font-size: 0.875rem; text-align: center; padding: 1rem;">No sessions yet</p>';
            return;
        }

        container.innerHTML = this.sessions.map(session => `
            <div class="session-item ${session.session_id === this.currentSessionId ? 'active' : ''}"
                 onclick="app.selectSession('${session.session_id}')">
                <div class="session-info">
                    <h4>${session.title}</h4>
                    <p>${new Date(session.created_at).toLocaleString()}</p>
                </div>
                <button onclick="event.stopPropagation(); app.deleteSession('${session.session_id}')" 
                        class="btn btn-danger btn-small">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `).join('');
    }

    async selectSession(sessionId) {
        this.currentSessionId = sessionId;
        await this.loadSessionMessages();
        this.renderSessions();
        this.updateUI();
    }

    async loadSessionMessages() {
        if (!this.currentSessionId) return;

        try {
            const response = await fetch(`${this.apiBase}/api/chat/sessions/${this.currentSessionId}/messages`);
            const messages = await response.json();
            this.renderMessages(messages);
        } catch (error) {
            console.error('Failed to load messages:', error);
        }
    }

    renderMessages(messages) {
        const container = document.getElementById('messages-container');
        
        if (messages.length === 0) {
            container.innerHTML = `
                <div class="welcome-message">
                    <div class="welcome-content">
                        <i class="fas fa-comments"></i>
                        <h3>Start a conversation!</h3>
                        <p>Ask questions about your data in natural language.</p>
                    </div>
                </div>
            `;
            return;
        }

        container.innerHTML = messages.map(message => {
            const isUser = message.type === 'user';
            const content = isUser ? message.content : this.formatAssistantMessage(message.content);
            
            return `
                <div class="message message-${message.type}">
                    <div class="message-content">
                        ${content}
                        <div class="message-timestamp">
                            ${new Date(message.timestamp).toLocaleString()}
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        container.scrollTop = container.scrollHeight;
    }

    formatAssistantMessage(content) {
        try {
            const data = JSON.parse(content);
            if (data.columns && data.rows) {
                return this.createDataTable(data.columns, data.rows);
            }
            return content;
        } catch {
            return content;
        }
    }

    createDataTable(columns, rows) {
        if (rows.length === 0) {
            return '<p>No data found.</p>';
        }

        const maxRows = 50; // Limit display
        const displayRows = rows.slice(0, maxRows);
        const hasMore = rows.length > maxRows;

        return `
            <div class="data-table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            ${columns.map(col => `<th>${col}</th>`).join('')}
                        </tr>
                    </thead>
                    <tbody>
                        ${displayRows.map(row => `
                            <tr>
                                ${row.map(cell => `<td>${cell !== null ? cell : '<em>null</em>'}</td>`).join('')}
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
                <div style="margin-top: 0.5rem; font-size: 0.875rem; color: var(--text-secondary);">
                    Showing ${displayRows.length} of ${rows.length} results
                    ${hasMore ? '(limited for display)' : ''}
                </div>
            </div>
        `;
    }

    async sendMessage() {
        const input = document.getElementById('message-input');
        const message = input.value.trim();
        
        if (!message || !this.connectionId || !this.currentSessionId) return;

        // Get selected query mode
        const queryMode = document.querySelector('input[name="query-mode"]:checked').value;
        const endpoint = queryMode === 'direct' ? '/api/chat/query-direct' : '/api/chat/query';

        // Add user message to UI
        this.addMessage(message, 'user');
        input.value = '';

        // Create assistant message container for streaming
        const assistantMessageDiv = this.addMessage('', 'assistant', true);
        const contentDiv = assistantMessageDiv.querySelector('.message-content');

        try {
            const response = await fetch(`${this.apiBase}${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    connection_id: this.connectionId,
                    message: message,
                    session_id: this.currentSessionId
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.trim()) {
                        try {
                            const event = JSON.parse(line);
                            this.handleStreamingEvent(event, contentDiv);
                        } catch (e) {
                            console.error('Failed to parse streaming event:', line, e);
                        }
                    }
                }
            }

        } catch (error) {
            contentDiv.innerHTML = `
                <div class="streaming-event event-error">
                    <strong>Error:</strong> ${error.message}
                </div>
            `;
            this.showToast(`Query failed: ${error.message}`, 'error');
        }

        this.scrollToBottom();
    }

    handleStreamingEvent(event, contentDiv) {
        const eventDiv = document.createElement('div');
        eventDiv.className = 'streaming-event';

        switch (event.event) {
            case 'start':
                const mode = event.mode || 'react';
                const modeText = mode === 'direct_llm' ? 'Direct LLM' : 'ReAct Agent';
                eventDiv.innerHTML = `<strong>🤖 Processing with ${modeText}...</strong>`;
                break;
            
            case 'cache_hit':
                eventDiv.className += ' event-cache-hit';
                eventDiv.innerHTML = `<strong>⚡ Cache Hit!</strong> Similar query found (${Math.round(event.similarity * 100)}% match)`;
                break;
            
            case 'agent_started':
                eventDiv.innerHTML = `<strong>🔄 Agent Started:</strong> ${event.mode.toUpperCase()} mode`;
                break;
            
            case 'llm_processing':
                eventDiv.innerHTML = `<strong>🧠 LLM Processing:</strong> ${event.message}`;
                break;
            
            case 'llm_response':
                eventDiv.innerHTML = `<strong>💭 LLM Response:</strong> Analyzing...`;
                break;
            
            case 'generated_sql':
                eventDiv.className += ' event-sql';
                const explanation = event.explanation ? `<br><em>${event.explanation}</em>` : '';
                eventDiv.innerHTML = `<strong>💡 Generated SQL:</strong><br><code>${event.sql}</code>${explanation}`;
                break;
            
            case 'generated_filter':
                eventDiv.className += ' event-sql';
                const mongoExplanation = event.explanation ? `<br><em>${event.explanation}</em>` : '';
                const collectionInfo = event.collection ? `<br>Collection: <code>${event.collection}</code>` : '';
                eventDiv.innerHTML = `<strong>💡 Generated MongoDB Query:</strong>${collectionInfo}<br>Filter: <code>${JSON.stringify(event.filter, null, 2)}</code>${mongoExplanation}`;
                break;
            
            case 'executing_sql':
            case 'executing_query':
                eventDiv.innerHTML = `<strong>⚡ Executing:</strong> ${event.message}`;
                break;
            
            case 'generated_message':
                eventDiv.innerHTML = `<strong>💬 Generated Message:</strong> ${event.message}`;
                break;
            
            case 'result':
                const table = this.createDataTable(event.data.columns, event.data.rows);
                const resultExplanation = event.data.explanation ? `<p><em>${event.data.explanation}</em></p>` : '';
                eventDiv.innerHTML = `<strong>📊 Results:</strong>${resultExplanation}${table}`;
                break;
            
            case 'conversation':
                eventDiv.className += ' event-conversation';
                eventDiv.innerHTML = `<strong>💬 Assistant:</strong> ${event.message}`;
                break;
            
            case 'agent_error':
            case 'error':
            case 'sql_error':
            case 'query_error':
                eventDiv.className += ' event-error';
                eventDiv.innerHTML = `<strong>❌ Error:</strong> ${event.message}`;
                break;
            
            case 'end':
                eventDiv.innerHTML = '<strong>✅ Query completed!</strong>';
                break;
            
            default:
                eventDiv.innerHTML = `<strong>${event.event}:</strong> ${JSON.stringify(event)}`;
        }

        contentDiv.appendChild(eventDiv);
        this.scrollToBottom();
    }

    addMessage(content, type, isStreaming = false) {
        const container = document.getElementById('messages-container');
        
        // Remove welcome message if present
        const welcome = container.querySelector('.welcome-message');
        if (welcome) welcome.remove();

        const messageDiv = document.createElement('div');
        messageDiv.className = `message message-${type}`;
        
        messageDiv.innerHTML = `
            <div class="message-content">
                ${isStreaming ? '' : content}
                <div class="message-timestamp">
                    ${new Date().toLocaleString()}
                </div>
            </div>
        `;

        container.appendChild(messageDiv);
        this.scrollToBottom();
        
        return messageDiv;
    }

    async deleteSession(sessionId) {
        if (!confirm('Are you sure you want to delete this session?')) return;

        try {
            await fetch(`${this.apiBase}/api/chat/sessions/${sessionId}`, {
                method: 'DELETE'
            });

            if (sessionId === this.currentSessionId) {
                this.currentSessionId = null;
                document.getElementById('messages-container').innerHTML = `
                    <div class="welcome-message">
                        <div class="welcome-content">
                            <i class="fas fa-robot"></i>
                            <h3>Session deleted</h3>
                            <p>Create a new session to start chatting.</p>
                        </div>
                    </div>
                `;
            }

            await this.loadSessions();
            this.updateUI();
            this.showToast('Session deleted!', 'info');
        } catch (error) {
            this.showToast(`Failed to delete session: ${error.message}`, 'error');
        }
    }

    clearChat() {
        if (!confirm('Clear current chat? This will create a new session.')) return;
        this.createNewSession();
    }

    exportChat() {
        if (!this.currentSessionId) {
            this.showToast('No active session to export', 'info');
            return;
        }

        const messages = Array.from(document.querySelectorAll('.message')).map(msg => ({
            type: msg.classList.contains('message-user') ? 'user' : 'assistant',
            content: msg.querySelector('.message-content').textContent.trim(),
            timestamp: msg.querySelector('.message-timestamp').textContent.trim()
        }));

        const exportData = {
            session_id: this.currentSessionId,
            exported_at: new Date().toISOString(),
            messages: messages
        };

        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `chat-export-${this.currentSessionId}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        this.showToast('Chat exported successfully!', 'success');
    }

    updateUI() {
        // Update connection status
        const statusEl = document.getElementById('connection-status');
        statusEl.className = `status ${this.isConnected ? 'connected' : 'disconnected'}`;
        statusEl.innerHTML = `<i class="fas fa-circle"></i> ${this.isConnected ? 'Connected' : 'Disconnected'}`;

        // Update connection info visibility
        document.getElementById('connection-info').classList.toggle('hidden', !this.isConnected);

        // Update input state
        const messageInput = document.getElementById('message-input');
        const sendBtn = document.getElementById('send-btn');
        const canChat = this.isConnected && this.currentSessionId;
        
        messageInput.disabled = !canChat;
        sendBtn.disabled = !canChat;

        // Update session title
        const currentSessionTitle = document.getElementById('current-session');
        if (this.currentSessionId) {
            const session = this.sessions.find(s => s.session_id === this.currentSessionId);
            currentSessionTitle.textContent = session ? session.title : 'Current Session';
        } else {
            currentSessionTitle.textContent = 'No Session Selected';
        }

        // Update input status
        const statusMsg = document.getElementById('input-status');
        if (!this.isConnected) {
            statusMsg.textContent = 'Connect to a database first';
        } else if (!this.currentSessionId) {
            statusMsg.textContent = 'Create or select a chat session';
        } else {
            statusMsg.textContent = 'Ready to chat!';
        }
    }

    scrollToBottom() {
        const container = document.getElementById('messages-container');
        container.scrollTop = container.scrollHeight;
    }

    showLoading(show) {
        document.getElementById('loading-overlay').classList.toggle('hidden', !show);
    }

    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        const icon = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            info: 'fas fa-info-circle'
        }[type] || 'fas fa-info-circle';

        toast.innerHTML = `
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <i class="${icon}"></i>
                <span>${message}</span>
            </div>
        `;

        container.appendChild(toast);

        // Auto remove after 5 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 5000);
    }
}

// Initialize the app
const app = new DatabaseChatbot();
