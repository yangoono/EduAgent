// static/js/course_manager.js

const courseManager = {
    modalInstance: null,
    exportButton: null,
    importButton: null,
    isProcessing: false,

    // 初始化方法
    init(modal, { exportBtn, importBtn } = {}) {
        this.modalInstance = modal;
        
        // 优先使用传入的按钮引用，找不到再通过ID查找
        this.exportButton = exportBtn || document.getElementById('export-courses-btn');
        this.importButton = importBtn || document.getElementById('import-courses-btn');
        this.bindEvents();
        this.loadCourses();
    },

    // 事件绑定
    bindEvents() {
        // 基础操作事件
        document.getElementById('add-course-btn').addEventListener('click', () => this.showModal());
        document.getElementById('save-course-btn').addEventListener('click', () => this.saveCourse());
        document.getElementById('course-search-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.loadCourses();
        });

        // 导出/导入事件
        if (this.exportButton) {
            this.exportButton.addEventListener('click', () => this.exportCoursesCsv());
        } else {
            console.warn('导出按钮未找到');
        }

        if (this.importButton) {
            this.importButton.addEventListener('click', () => this.prepareImport());
        } else {
            console.warn('导入按钮未找到');
        }
    },

    // 加载课程数据
    async loadCourses() {
        if (this.isProcessing) return;
        
        try {
            this.setLoadingState(true);
            const params = this.getSearchParams();
            const res = await fetch(`/api/courses?${params}`);
            
            if (!res.ok) throw new Error(`HTTP错误: ${res.status}`);
            
            const data = await res.json();
            this.renderCourses(Array.isArray(data) ? data : (data.data || []));
        } catch (error) {
            console.error('加载失败:', error);
            this.showError('加载课程数据失败');
        } finally {
            this.setLoadingState(false);
        }
    },

    // 渲染课程表格
    renderCourses(courses) {
        const tbody = document.getElementById('course-table-body');
        if (!courses || courses.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center">暂无课程数据</td></tr>';
            return;
        }

        tbody.innerHTML = courses.map(course => `
            <tr data-cno="${course.cno}">
                <td>${course.cno}</td>
                <td>${course.cname}</td>
                <td>${course.cpno || '无'}</td>
                <td>${course.ccredit}</td>
                <td>${course.cteacher}</td>
                <td class="text-end">
                    <button class="btn btn-sm btn-outline-primary edit-course-btn">编辑</button>
                    <button class="btn btn-sm btn-outline-danger delete-course-btn">删除</button>
                </td>
            </tr>
        `).join('');

        this.addTableListeners();
    },

    // 表格操作事件
    addTableListeners() {
        document.querySelectorAll('.edit-course-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const cno = e.target.closest('tr').dataset.cno;
                this.showModal(cno);
            });
        });

        document.querySelectorAll('.delete-course-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const cno = e.target.closest('tr').dataset.cno;
                if (confirm(`确定删除课程 ${cno} 吗？所有关联数据也将被删除！`)) {
                    await this.deleteCourse(cno);
                }
            });
        });
    },

    // 显示编辑模态框
    async showModal(cno = null) {
        const form = document.getElementById('course-form');
        form.reset();
        
        await this.populateCpnoSelect(cno);
        
        document.getElementById('course-modal-title').textContent = cno ? '编辑课程' : '添加课程';
        document.getElementById('course-cno').disabled = !!cno;
        
        if (cno) {
            try {
                const res = await fetch(`/api/courses/${cno}`);
                if (!res.ok) throw new Error('加载失败');
                
                const course = await res.json();
                document.getElementById('course-cno-hidden').value = cno;
                document.getElementById('course-cno').value = course.cno;
                document.getElementById('course-cname').value = course.cname;
                document.getElementById('course-cpno').value = course.cpno || '';
                document.getElementById('course-ccredit').value = course.ccredit;
                document.getElementById('course-cteacher').value = course.cteacher;
            } catch (error) {
                this.showError('加载课程信息失败');
                return;
            }
        }
        
        this.modalInstance.show();
    },

    // 填充先修课程下拉框
    async populateCpnoSelect(excludeCno = null) {
        try {
            const res = await fetch('/api/courses');
            const courses = await res.json();
            const select = document.getElementById('course-cpno');
            
            select.innerHTML = '<option value="">无</option>' +
                courses
                    .filter(c => c.cno !== excludeCno)
                    .map(c => `<option value="${c.cno}">${c.cname} (${c.cno})</option>`)
                    .join('');
        } catch (error) {
            console.error('加载先修课程失败:', error);
            document.getElementById('course-cpno').innerHTML = '<option value="">无</option>';
        }
    },

    // 保存课程
    async saveCourse() {
        if (this.isProcessing) return;
        
        const form = document.getElementById('course-form');
        const isEdit = !!document.getElementById('course-cno-hidden').value;
        
        const courseData = {
            cno: form.cno.value.trim(),
            cname: form.cname.value.trim(),
            cpno: form.cpno.value || null,
            ccredit: parseInt(form.ccredit.value),
            cteacher: form.cteacher.value.trim()
        };

        // 前端验证
        if (!this.validateCourse(courseData)) return;

        try {
            this.setProcessingState(true);
            
            const url = isEdit 
                ? `/api/courses/${document.getElementById('course-cno-hidden').value}`
                : '/api/courses';
                
            const method = isEdit ? 'PUT' : 'POST';
            
            const res = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(courseData)
            });
            
            const result = await res.json();
            
            if (!res.ok) {
                throw new Error(result.message || '操作失败');
            }
            
            this.modalInstance.hide();
            this.showSuccess(isEdit ? '课程更新成功' : '课程添加成功');
            this.loadCourses();
        } catch (error) {
            this.showError(error.message || '保存失败');
        } finally {
            this.setProcessingState(false);
        }
    },

    // 删除课程
    async deleteCourse(cno) {
        if (this.isProcessing) return;
        
        try {
            this.setProcessingState(true);
            const res = await fetch(`/api/courses/${cno}`, { method: 'DELETE' });
            
            if (!res.ok) {
                const error = await res.json();
                throw new Error(error.message || '删除失败');
            }
            
            this.showSuccess('课程已删除');
            this.loadCourses();
        } catch (error) {
            this.showError(error.message || '删除失败');
        } finally {
            this.setProcessingState(false);
        }
    },

    // 导出CSV
    async exportCoursesCsv() {
        if (this.isProcessing) return;
        
        try {
            this.setProcessingState(true, this.exportButton);
            
            const params = this.getSearchParams();
            const res = await fetch(`/api/courses/export?${params}`);
            
            if (!res.ok) throw new Error(`导出失败: ${res.status}`);
            if (res.status === 204) throw new Error('没有可导出的数据');
            
            const blob = await res.blob();
            this.downloadFile(blob, `courses_${new Date().toISOString().slice(0,10)}.csv`);
            
            this.showSuccess('导出成功');
        } catch (error) {
            this.showError(error.message || '导出失败');
        } finally {
            this.setProcessingState(false, this.exportButton);
        }
    },

    // 准备导入
    prepareImport() {
        if (this.isProcessing) return;
        
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.accept = '.csv';
        
        fileInput.onchange = async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            
            if (!confirm(`确定要导入 ${file.name} 吗？这将覆盖现有课程数据！`)) {
                return;
            }
            
            await this.importCoursesCsv(file);
        };
        
        fileInput.click();
    },

    // 导入CSV
    async importCoursesCsv(file) {
        if (this.isProcessing) return;
        
        try {
            this.setProcessingState(true, this.importButton);
            
            const formData = new FormData();
            formData.append('file', file);
            
            const res = await fetch('/api/courses/import', {
                method: 'POST',
                body: formData
            });
            
            const result = await res.json();
            
            if (!res.ok) {
                throw new Error(result.message || '导入失败');
            }
            
            this.showSuccess(`成功导入 ${result.imported} 条课程记录`);
            this.loadCourses();
        } catch (error) {
            this.showError(error.message || '导入失败');
        } finally {
            this.setProcessingState(false, this.importButton);
        }
    },

    // ===== 工具方法 =====
    getSearchParams() {
        const search = document.getElementById('course-search-input').value || '';
        const teacher = document.getElementById('course-search-teacher').value || '';
        const credit = document.getElementById('course-search-credit').value || '';
        
        return new URLSearchParams({
            search: encodeURIComponent(search),
            teacher: encodeURIComponent(teacher),
            credit: encodeURIComponent(credit)
        }).toString();
    },

    validateCourse(data) {
        if (!data.cno || !/^[A-Za-z0-9]{3,10}$/.test(data.cno)) {
            this.showError('课程号必须为3-10位字母数字组合');
            return false;
        }
        
        if (!data.cname || data.cname.length > 50) {
            this.showError('课程名不能为空且不超过50字符');
            return false;
        }
        
        if (isNaN(data.ccredit) || data.ccredit < 0 || data.ccredit > 10) {
            this.showError('学分必须为0-10的数字');
            return false;
        }
        
        if (!data.cteacher || data.cteacher.length > 20) {
            this.showError('教师姓名不能为空且不超过20字符');
            return false;
        }
        
        return true;
    },

    downloadFile(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    },

    setLoadingState(isLoading) {
        const spinner = document.getElementById('course-loading-spinner');
        if (spinner) {
            spinner.style.display = isLoading ? 'inline-block' : 'none';
        }
    },

    setProcessingState(isProcessing, button = null) {
        this.isProcessing = isProcessing;
        
        if (button) {
            button.disabled = isProcessing;
            button.innerHTML = isProcessing 
                ? '<span class="spinner-border spinner-border-sm"></span> 处理中...'
                : button.dataset.originalText || button.textContent;
        }
    },

    showSuccess(message) {
        const toast = document.getElementById('success-toast');
        if (toast) {
            toast.querySelector('.toast-body').textContent = message;
            bootstrap.Toast.getOrCreateInstance(toast).show();
        }
    },

    showError(message) {
        const toast = document.getElementById('error-toast');
        if (toast) {
            toast.querySelector('.toast-body').textContent = message;
            bootstrap.Toast.getOrCreateInstance(toast).show();
        }
    }
};

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    const modalElement = document.getElementById('course-modal');
    if (modalElement) {
        courseManager.init(new bootstrap.Modal(modalElement));
    }
    
    // 保存按钮原始文本
    const exportBtn = document.getElementById('export-courses-btn');
    const importBtn = document.getElementById('import-courses-btn');
    if (exportBtn) exportBtn.dataset.originalText = exportBtn.textContent;
    if (importBtn) importBtn.dataset.originalText = importBtn.textContent;
});