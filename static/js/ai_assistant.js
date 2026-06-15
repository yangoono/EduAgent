document.addEventListener('DOMContentLoaded', function() {
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-msg-btn');
    const messagesArea = document.getElementById('chat-messages-area');
    const clearBtn = document.getElementById('clear-chat-btn');
    const imageInput = document.getElementById('chat-image-input');
    const uploadTrigger = document.getElementById('upload-image-trigger');
    const currentAgentBadge = document.getElementById('current-agent-badge');

    // 默认是学生角色
    let currentRole = 'student';
    let currentAgentName = '学生助手模型';

    if (window.currentUserRole) {
        currentRole = window.currentUserRole;
        if (currentRole === 'teacher') currentAgentName = '班主任助手模型';
        if (currentRole === 'admin') currentAgentName = '管理员监控模型';
        currentAgentBadge.innerHTML = `<i class="fas fa-robot me-1"></i> ${currentAgentName}`;
    }

    // 添加消息到聊天区域
    function appendMessage(role, content, echarts_option=null) {
        const isUser = role === 'user';
        const msgDiv = document.createElement('div');
        msgDiv.className = `d-flex mb-4 ${isUser ? 'justify-content-end user-message' : 'ai-message'}`;
        
        let avatarHTML = '';
        if (!isUser) {
            avatarHTML = `
                <div class="avatar bg-primary text-white rounded-circle d-flex justify-content-center align-items-center shadow-sm me-3 flex-shrink-0" style="width: 40px; height: 40px;">
                    <i class="fas fa-robot"></i>
                </div>`;
        }

        const bubbleWidth = echarts_option ? '95%' : '75%';
        let bubbleHTML = `
            <div class="message-bubble ${isUser ? 'bg-primary text-white' : 'bg-white text-dark'} shadow-sm rounded-4 p-3" style="max-width: ${bubbleWidth}; width: ${echarts_option ? '800px' : 'auto'};">
                <p class="mb-0" style="white-space: pre-wrap;">${content}</p>
        `;
        
        let chartId = null;
        if (echarts_option) {
            chartId = 'chart-' + Date.now();
            bubbleHTML += `<div id="${chartId}" style="width: 100%; height: 400px; margin-top: 15px;"></div>`;
        }
        
        bubbleHTML += `</div>`;

        msgDiv.innerHTML = isUser ? bubbleHTML : (avatarHTML + bubbleHTML);
        messagesArea.appendChild(msgDiv);
        messagesArea.scrollTop = messagesArea.scrollHeight;
        
        if (echarts_option && chartId) {
            setTimeout(() => {
                const chartDom = document.getElementById(chartId);
                if (chartDom && window.echarts) {
                    const myChart = window.echarts.init(chartDom);
                    myChart.setOption(echarts_option);
                    window.addEventListener('resize', function() {
                        myChart.resize();
                    });
                } else if (!window.echarts) {
                    console.error("ECharts is not loaded on this page!");
                }
            }, 100);
        }
    }

    // 渲染 Agent 思考过程（可折叠面板）
    function appendThinkingSteps(steps) {
        if (!steps || steps.length === 0) return;

        const stepId = `thinking-${Date.now()}`;
        const wrapper = document.createElement('div');
        wrapper.className = 'd-flex mb-2 ai-message';
        wrapper.style.paddingLeft = '52px'; // 对齐头像宽度

        const typeIconMap = {
            'thought': { icon: 'fa-brain', color: '#6f42c1', label: '思考' },
            'action': { icon: 'fa-bolt', color: '#fd7e14', label: '执行工具' },
            'observation': { icon: 'fa-database', color: '#198754', label: '工具返回' }
        };

        let stepsHTML = steps.map((step, idx) => {
            const t = typeIconMap[step.type] || { icon: 'fa-circle', color: '#6c757d', label: step.type };
            return `
                <div class="d-flex align-items-start mb-2">
                    <span style="color:${t.color}; min-width:90px; font-size:0.8rem; font-weight:600;">
                        <i class="fas ${t.icon} me-1"></i>${t.label}
                    </span>
                    <span class="text-muted" style="font-size:0.82rem; white-space:pre-wrap; word-break:break-all;">${escapeHtml(step.content)}</span>
                </div>`;
        }).join('');

        wrapper.innerHTML = `
            <div style="max-width:85%;">
                <div class="accordion accordion-flush" id="${stepId}">
                    <div class="accordion-item border rounded-3 shadow-sm bg-light">
                        <h2 class="accordion-header">
                            <button class="accordion-button collapsed py-2 px-3 rounded-3" type="button"
                                data-bs-toggle="collapse" data-bs-target="#${stepId}-body"
                                style="font-size:0.82rem; background:transparent; color:#6c757d;">
                                <i class="fas fa-code-branch me-2"></i>
                                查看 Agent 推理过程（${steps.length} 步）
                            </button>
                        </h2>
                        <div id="${stepId}-body" class="accordion-collapse collapse">
                            <div class="accordion-body py-2 px-3" style="font-size:0.82rem;">
                                ${stepsHTML}
                            </div>
                        </div>
                    </div>
                </div>
            </div>`;

        messagesArea.appendChild(wrapper);
        messagesArea.scrollTop = messagesArea.scrollHeight;
    }

    function escapeHtml(text) {
        return String(text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    // 显示加载动画
    function showTypingIndicator() {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'd-flex mb-4 ai-message typing-indicator-container';
        msgDiv.innerHTML = `
            <div class="avatar bg-primary text-white rounded-circle d-flex justify-content-center align-items-center shadow-sm me-3 flex-shrink-0" style="width: 40px; height: 40px;">
                <i class="fas fa-robot"></i>
            </div>
            <div class="message-bubble bg-white shadow-sm rounded-4 p-3 d-flex align-items-center">
                <div class="typing-indicator">
                    <span></span><span></span><span></span>
                </div>
            </div>
        `;
        messagesArea.appendChild(msgDiv);
        messagesArea.scrollTop = messagesArea.scrollHeight;
        return msgDiv;
    }

    // 发送文本消息
    async function sendMessage() {
        const text = chatInput.value.trim();
        if (!text) return;

        appendMessage('user', text);
        chatInput.value = '';

        const typingIndicator = showTypingIndicator();

        try {
            const response = await fetch(`/api/agent/${currentRole}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });

            const data = await response.json();
            typingIndicator.remove();

            if (response.ok && data.reply) {
                // 先展示思考过程（如果有）
                if (data.thinking_steps && data.thinking_steps.length > 0) {
                    appendThinkingSteps(data.thinking_steps);
                }
                // 再展示最终答案
                appendMessage('ai', data.reply, data.echarts_option);
            } else {
                appendMessage('ai', '系统异常，请检查本地 MiniCPM-V 模型服务是否启动。');
            }
        } catch (error) {
            console.error('Chat error:', error);
            typingIndicator.remove();
            appendMessage('ai', '网络错误或本地大模型服务未响应，请检查终端！');
        }
    }

    // 处理图片上传进行 OCR
    async function handleImageUpload(e) {
        const file = e.target.files[0];
        if (!file) return;

        appendMessage('user', `[上传了一张图片: ${file.name}]`);
        const typingIndicator = showTypingIndicator();

        const reader = new FileReader();
        reader.onload = async function(event) {
            const base64String = event.target.result.split(',')[1];

            try {
                const response = await fetch('/api/edge/ocr', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ image_base64: base64String })
                });

                const data = await response.json();
                typingIndicator.remove();

                if (response.ok && data.data) {
                    const extracted = data.data;
                    let replyText = `📸 端侧隐私提取完成\n\n已成功从图片中提取结构化数据，且图片原件已被内存销毁。\n提取结果：\n`;
                    replyText += `• 学号: ${extracted.sno || '未知'}\n`;
                    replyText += `• 成绩: ${extracted.score || '未知'}\n\n`;
                    replyText += `你可以继续问我关于如何提高成绩的建议！`;
                    appendMessage('ai', replyText);
                } else {
                    appendMessage('ai', `图片解析失败: ${data.error || '未知错误'}`);
                }
            } catch (error) {
                console.error('OCR error:', error);
                typingIndicator.remove();
                appendMessage('ai', 'OCR解析服务出错，请检查 MiniCPM-V 是否在本地运行！');
            }
        };
        reader.readAsDataURL(file);
        e.target.value = '';
    }

    // 事件绑定
    sendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') sendMessage();
    });

    uploadTrigger.addEventListener('click', () => imageInput.click());
    imageInput.addEventListener('change', handleImageUpload);

    clearBtn.addEventListener('click', () => {
        while (messagesArea.children.length > 1) {
            messagesArea.removeChild(messagesArea.lastChild);
        }
    });
});
