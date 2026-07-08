/**
 * EduAgent — AI Assistant Panel
 * Supports SSE streaming via /api/agent/stream.
 */
document.addEventListener('DOMContentLoaded', function () {

    const chatInput      = document.getElementById('ai-chat-input');
    const sendBtn        = document.getElementById('send-btn');
    const messagesArea   = document.getElementById('chat-messages-area');
    const clearBtn       = document.getElementById('clear-chat-btn');
    const imageInput     = document.getElementById('chat-image-input');
    const uploadTrigger  = document.getElementById('upload-image-trigger');
    const agentBadge     = document.getElementById('current-agent-badge');

    // ── Role detection ───────────────────────────────────────
    let currentRole = window.currentUserRole || 'student';
    const roleLabels = {
        student: '学生助手',
        teacher: '教师助手',
        admin:   '管理员助手'
    };
    if (agentBadge) {
        agentBadge.innerHTML = `<i class="fas fa-robot me-1"></i>${roleLabels[currentRole] || '智能助手'}`;
    }

    // ── Helpers ──────────────────────────────────────────────
    function escapeHtml(text) {
        return String(text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function renderMarkdown(text) {
        // Simple markdown: **bold**, `code`, newlines
        return escapeHtml(text)
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/`([^`]+)`/g, '<code style="background:rgba(99,102,241,0.15);padding:0.1em 0.4em;border-radius:4px;font-size:0.85em">$1</code>')
            .replace(/\n/g, '<br>');
    }

    function scrollBottom() {
        messagesArea.scrollTop = messagesArea.scrollHeight;
    }

    // ── Append final message bubble ──────────────────────────
    function appendMessage(role, content, echartsOption = null) {
        const isUser = role === 'user';
        const wrapper = document.createElement('div');
        wrapper.className = `d-flex mb-4 align-items-end ${isUser ? 'justify-content-end user-message' : 'ai-message'}`;

        const bubbleMaxW = echartsOption ? '95%' : '78%';
        const bubbleStyle = `max-width:${bubbleMaxW};`;

        let avatar = '';
        if (!isUser) {
            avatar = `<div class="ai-avatar me-2 flex-shrink-0"><i class="fas fa-robot"></i></div>`;
        }

        const chartId = echartsOption ? `chart-${Date.now()}` : null;
        const chartHtml = chartId
            ? `<div id="${chartId}" style="width:100%;height:400px;margin-top:12px;border-radius:8px;overflow:hidden;"></div>`
            : '';

        const bubbleContent = isUser
            ? escapeHtml(content)
            : renderMarkdown(content);

        const bubble = `
            <div class="message-bubble p-3" style="${bubbleStyle}">
                <p class="mb-0" style="line-height:1.7;white-space:pre-wrap;">${bubbleContent}</p>
                ${chartHtml}
            </div>`;

        wrapper.innerHTML = isUser ? bubble : (avatar + bubble);
        messagesArea.appendChild(wrapper);
        scrollBottom();

        if (chartId && window.echarts) {
            setTimeout(() => {
                const dom = document.getElementById(chartId);
                if (dom) {
                    const chart = window.echarts.init(dom);
                    chart.setOption(echartsOption);
                    window.addEventListener('resize', () => chart.resize());
                }
            }, 120);
        }
    }

    // ── Typing indicator ─────────────────────────────────────
    function showTyping() {
        const el = document.createElement('div');
        el.className = 'd-flex mb-4 ai-message align-items-end typing-indicator-container';
        el.innerHTML = `
            <div class="ai-avatar me-2 flex-shrink-0"><i class="fas fa-robot"></i></div>
            <div class="message-bubble p-3">
                <div class="typing-indicator"><span></span><span></span><span></span></div>
            </div>`;
        messagesArea.appendChild(el);
        scrollBottom();
        return el;
    }

    // ── SSE live thinking panel ──────────────────────────────
    function createLivePanel() {
        const wrapper = document.createElement('div');
        wrapper.className = 'd-flex mb-3 ai-message';
        wrapper.innerHTML = `
            <div class="ai-avatar me-2 flex-shrink-0" style="opacity:0.6;"><i class="fas fa-cog fa-spin"></i></div>
            <div class="thinking-panel" style="flex:1;max-width:85%;">
                <div class="thinking-header" id="thinking-toggle-${Date.now()}">
                    <i class="fas fa-brain" style="color:var(--primary-light);"></i>
                    <span style="font-weight:600;color:var(--text-secondary);">Agent 推理中...</span>
                    <span class="ms-auto" style="color:var(--text-muted);font-size:0.75rem;">点击展开</span>
                </div>
                <div class="thinking-body" id="thinking-steps-live"></div>
            </div>`;
        messagesArea.appendChild(wrapper);
        scrollBottom();

        const header = wrapper.querySelector('.thinking-header');
        const panel  = wrapper.querySelector('.thinking-panel');
        const body   = wrapper.querySelector('#thinking-steps-live');
        header.addEventListener('click', () => panel.classList.toggle('open'));

        return { wrapper, body, panel };
    }

    const typeConfig = {
        thought:     { label: 'THOUGHT',  cls: 'thought' },
        action:      { label: 'ACTION',   cls: 'action'  },
        observation: { label: 'RESULT',   cls: 'observation' },
    };

    function appendLiveStep(body, msg) {
        const type = Object.keys(typeConfig).find(k => msg.toLowerCase().startsWith(`[${k}`)) || 'thought';
        const cfg  = typeConfig[type] || typeConfig.thought;
        const row  = document.createElement('div');
        row.className = 'sse-step-ticker';
        row.innerHTML = `
            <span class="step-badge ${cfg.cls}">${cfg.label}</span>
            <span style="color:var(--text-secondary);font-size:0.8rem;line-height:1.5;">${escapeHtml(msg)}</span>`;
        body.appendChild(row);
        scrollBottom();
    }

    // ── Send message (SSE) ───────────────────────────────────
    async function sendMessage() {
        const text = chatInput.value.trim();
        if (!text) return;

        appendMessage('user', text);
        chatInput.value = '';
        sendBtn.disabled = true;
        chatInput.disabled = true;

        // Build the SSE URL + POST via EventSource-compatible method
        // Since EventSource doesn't support POST, use fetch streaming
        const token = localStorage.getItem('jwt_token');
        const headers = {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        };

        let livePanel = null;

        try {
            const response = await fetch('/api/agent/stream', {
                method: 'POST',
                headers,
                body: JSON.stringify({ message: text })
            });

            if (!response.ok) {
                appendMessage('ai', `请求失败 (${response.status})，请检查服务状态。`);
                return;
            }

            const reader  = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer    = '';
            let finalResult = null;

            livePanel = createLivePanel();

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });

                // Parse SSE lines
                const lines = buffer.split('\n');
                buffer = lines.pop(); // keep incomplete line

                for (const line of lines) {
                    if (!line.startsWith('data:')) continue;
                    const raw = line.slice(5).trim();
                    if (!raw) continue;
                    try {
                        const event = JSON.parse(raw);
                        if (event.type === 'step') {
                            appendLiveStep(livePanel.body, event.content);
                        } else if (event.type === 'done') {
                            finalResult = event;
                        } else if (event.type === 'error') {
                            finalResult = { answer: `系统错误: ${event.content}`, echarts_option: null };
                        }
                    } catch (_) { /* ignore malformed lines */ }
                }
            }

            // Finalise live panel
            if (livePanel) {
                const header = livePanel.panel.querySelector('.thinking-header span');
                if (header) header.textContent = `Agent 推理完成（${livePanel.body.children.length} 步）`;
                livePanel.panel.querySelector('.ai-avatar .fa-cog')?.classList.remove('fa-spin');
            }

            // Render final answer
            if (finalResult) {
                appendMessage('ai', finalResult.answer || '（无回复）', finalResult.echarts_option);
            }

        } catch (err) {
            console.error('[SSE] Error:', err);
            if (livePanel) livePanel.wrapper.remove();
            appendMessage('ai', `网络错误：${err.message}`);
        } finally {
            sendBtn.disabled = false;
            chatInput.disabled = false;
            chatInput.focus();
        }
    }

    // ── Image upload (OCR) ───────────────────────────────────
    async function handleImageUpload(e) {
        const file = e.target.files[0];
        if (!file) return;
        appendMessage('user', `[上传图片: ${file.name}]`);
        const typing = showTyping();

        const reader = new FileReader();
        reader.onload = async function (ev) {
            const b64 = ev.target.result.split(',')[1];
            try {
                const res  = await fetch('/api/edge/ocr', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ image_base64: b64 })
                });
                const data = await res.json();
                typing.remove();
                if (res.ok && data.data) {
                    const d = data.data;
                    appendMessage('ai',
                        `端侧隐私提取完成\n\n已从图片提取结构化数据，原图已内存销毁。\n\n学号：${d.sno || '未知'}\n成绩：${d.score || '未知'}\n\n你可以继续询问成绩分析建议！`
                    );
                } else {
                    appendMessage('ai', `图片解析失败：${data.error || '未知错误'}`);
                }
            } catch (err) {
                typing.remove();
                appendMessage('ai', `OCR 服务异常：${err.message}`);
            }
        };
        reader.readAsDataURL(file);
        e.target.value = '';
    }

    // ── Event bindings ───────────────────────────────────────
    sendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    uploadTrigger?.addEventListener('click', () => imageInput.click());
    imageInput?.addEventListener('change', handleImageUpload);
    clearBtn?.addEventListener('click', () => {
        while (messagesArea.children.length > 1) {
            messagesArea.removeChild(messagesArea.lastChild);
        }
    });
});
