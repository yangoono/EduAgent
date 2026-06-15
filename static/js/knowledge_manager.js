document.addEventListener('DOMContentLoaded', () => {
    const knowledgeTableBody = document.getElementById('knowledge-table-body');
    const pdfFileInput = document.getElementById('pdf-file');
    const confirmPdfUploadBtn = document.getElementById('confirm-pdf-upload');
    const pdfUploadSpinner = document.getElementById('pdf-upload-spinner');
    
    // 监听导航点击，进入知识库视图时加载数据
    const knowledgeNavLink = document.querySelector('a[data-view="knowledge-view"]');
    if (knowledgeNavLink) {
        knowledgeNavLink.addEventListener('click', () => {
            loadKnowledgeDocs();
        });
    }

    function loadKnowledgeDocs() {
        if (!knowledgeTableBody) return;
        
        window.api.get('/api/rag/docs')
            .then(docs => {
                knowledgeTableBody.innerHTML = '';
                if (docs.length === 0) {
                    knowledgeTableBody.innerHTML = '<tr><td colspan="3" class="text-center text-muted py-4">知识库目前为空</td></tr>';
                    return;
                }
                docs.forEach(doc => {
                    const tr = document.createElement('tr');
                    
                    const contentPreview = doc.content.length > 50 ? doc.content.substring(0, 50) + '...' : doc.content;
                    
                    tr.innerHTML = `
                        <td>${doc.id}</td>
                        <td><strong>${doc.title}</strong></td>
                        <td><span class="text-muted small">${contentPreview}</span></td>
                    `;
                    knowledgeTableBody.appendChild(tr);
                });
            })
            .catch(error => {
                console.error('Failed to load knowledge docs:', error);
                window.utils.showToast('加载知识库文档失败', 'danger');
            });
    }

    if (confirmPdfUploadBtn) {
        confirmPdfUploadBtn.addEventListener('click', () => {
            const file = pdfFileInput.files[0];
            if (!file) {
                window.utils.showToast('请先选择一个PDF文件', 'warning');
                return;
            }

            const formData = new FormData();
            formData.append('file', file);

            // UI 状态
            confirmPdfUploadBtn.disabled = true;
            pdfUploadSpinner.classList.remove('d-none');

            fetch('/api/rag/upload_pdf', {
                method: 'POST',
                body: formData
            })
            .then(res => res.json().then(data => ({ status: res.status, ok: res.ok, body: data })))
            .then(({ ok, body }) => {
                if (!ok) {
                    throw new Error(body.message || '上传失败');
                }
                window.utils.showToast(body.message || 'PDF 上传并解析成功！', 'success');
                // 关闭弹窗
                const modalEl = document.getElementById('upload-pdf-modal');
                if (modalEl) {
                    const modal = bootstrap.Modal.getInstance(modalEl);
                    if (modal) {
                        modal.hide();
                    } else {
                        // fallback
                        modalEl.classList.remove('show');
                        modalEl.style.display = 'none';
                        const backdrop = document.querySelector('.modal-backdrop');
                        if (backdrop) backdrop.remove();
                    }
                }
                pdfFileInput.value = ''; // 清空选择
                loadKnowledgeDocs(); // 刷新列表
            })
            .catch(error => {
                console.error('Upload error:', error);
                window.utils.showToast(error.message, 'danger');
            })
            .finally(() => {
                confirmPdfUploadBtn.disabled = false;
                pdfUploadSpinner.classList.add('d-none');
            });
        });
    }
});
