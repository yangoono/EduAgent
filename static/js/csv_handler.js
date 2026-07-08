// static/js/csv_handler.js

window.csvHandler = (() => {
    const MODAL_ID = 'csv-upload-modal';
    const CONFIRM_BTN_ID = 'confirm-csv-upload';
    const FILE_INPUT_ID = 'csv-file';
    const STATUS_CONTAINER_ID = 'csv-upload-status';

    let modalInstance = null;
    let confirmBtn = null;
    let fileInput = null;
    let statusContainer = null;

    const IMPORT_TYPES = {
        STUDENT: 'students',
        COURSE: 'courses',
        SCORE: 'scores'
    };

    const API_ENDPOINTS = {
        [IMPORT_TYPES.STUDENT]: '/api/students/import-csv',
        [IMPORT_TYPES.COURSE]: '/api/courses/import-csv',
        [IMPORT_TYPES.SCORE]: '/api/scores/import-csv'
    };

    const SUCCESS_MESSAGES = {
        [IMPORT_TYPES.STUDENT]: '学生数据导入成功',
        [IMPORT_TYPES.COURSE]: '课程数据导入成功',
        [IMPORT_TYPES.SCORE]: '成绩数据导入成功'
    };

    /**
     * 初始化CSV处理器
     * @param {bootstrap.Modal} bsModalInstance Bootstrap模态框实例
     */
    const init = (bsModalInstance) => {
        // 获取DOM元素
        modalInstance = bsModalInstance;
        confirmBtn = document.getElementById(CONFIRM_BTN_ID);
        fileInput = document.getElementById(FILE_INPUT_ID);
        statusContainer = document.getElementById(STATUS_CONTAINER_ID);

        // 验证元素
        if (!modalInstance) {
            console.error('CSV处理器初始化失败: 未提供有效的模态框实例');
            return;
        }

        if (!confirmBtn || !fileInput) {
            console.error('CSV处理器初始化失败: 缺少必要的DOM元素', {
                confirmBtnExists: !!confirmBtn,
                fileInputExists: !!fileInput
            });
            return;
        }

        // 绑定事件
        confirmBtn.addEventListener('click', handleUpload);
        document.getElementById(MODAL_ID).addEventListener('hidden.bs.modal', resetUploadForm);
    };

    /**
     * 打开上传模态框
     * @param {string} importType 导入类型 (students/courses/scores)
     * @param {object} options 配置选项
     * @param {function} [options.onSuccess] 成功回调
     * @param {function} [options.onError] 错误回调
     */
    const openUploadModal = (importType, options = {}) => {
        if (!Object.values(IMPORT_TYPES).includes(importType)) {
            console.error('无效的导入类型:', importType);
            return;
        }

        // 存储当前导入类型和回调
        window.currentCsvImport = {
            type: importType,
            onSuccess: options.onSuccess,
            onError: options.onError
        };

        // 更新UI提示
        if (statusContainer) {
            statusContainer.innerHTML = `
                <div class="alert alert-info">
                    准备导入${getImportTypeName(importType)}数据
                </div>
            `;
        }

        // 显示模态框
        if (modalInstance) {
            modalInstance.show();
        } else {
            console.error('无法打开模态框: modalInstance未初始化');
        }
    };

    /**
     * 处理文件上传
     */
    const handleUpload = async () => {
        if (!window.currentCsvImport) {
            showAlert('danger', '错误: 未设置导入类型');
            return;
        }

        const { type, onSuccess, onError } = window.currentCsvImport;
        const file = fileInput?.files?.[0];

        // 验证文件
        if (!file) {
            showAlert('danger', '请选择CSV文件');
            return;
        }

        if (!file.name.toLowerCase().endsWith('.csv')) {
            showAlert('danger', '仅支持CSV格式文件');
            return;
        }

        // 准备上传
        setLoading(true);
        showAlert('info', '正在上传文件，请稍候...');

        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('type', type);

            const response = await fetch(API_ENDPOINTS[type] || '/api/import-csv', {
                method: 'POST',
                body: formData
            });

            const result = await parseResponse(response);

            if (result.success) {
                showAlert('success', SUCCESS_MESSAGES[type] + (result.message ? `: ${result.message}` : ''));
                if (typeof onSuccess === 'function') {
                    onSuccess(result);
                }
                
                // 根据类型刷新对应页面
                refreshAfterImport(type);
                
                // 3秒后自动关闭模态框
                setTimeout(() => {
                    if (modalInstance) modalInstance.hide();
                }, 3000);
            } else {
                throw new Error(result.message || '导入失败');
            }
        } catch (error) {
            console.error('CSV导入错误:', error);
            showAlert('danger', `导入失败: ${error.message}`);
            if (typeof onError === 'function') {
                onError(error);
            }
        } finally {
            setLoading(false);
        }
    };

    /**
     * 解析API响应
     */
    const parseResponse = async (response) => {
        if (!response.ok) {
            const errorText = await response.text();
            try {
                const errorData = JSON.parse(errorText);
                throw new Error(errorData.message || `服务器错误 (${response.status})`);
            } catch {
                throw new Error(errorText || `服务器错误 (${response.status})`);
            }
        }
        return response.json();
    };

    /**
     * 导入成功后刷新对应页面
     */
    const refreshAfterImport = (type) => {
        const managers = {
            [IMPORT_TYPES.STUDENT]: window.studentManager,
            [IMPORT_TYPES.COURSE]: window.courseManager,
            [IMPORT_TYPES.SCORE]: window.scoreManager
        };

        const refreshMethods = {
            [IMPORT_TYPES.STUDENT]: 'loadStudents',
            [IMPORT_TYPES.COURSE]: 'loadCourses',
            [IMPORT_TYPES.SCORE]: 'loadScores'
        };

        const manager = managers[type];
        const method = refreshMethods[type];

        if (manager && typeof manager[method] === 'function') {
            console.log(`自动刷新${getImportTypeName(type)}数据`);
            manager[method]();
        }
    };

    /**
     * 重置上传表单
     */
    const resetUploadForm = () => {
        if (fileInput) fileInput.value = '';
        if (statusContainer) statusContainer.innerHTML = '';
        window.currentCsvImport = null;
    };

    /**
     * 设置加载状态
     */
    const setLoading = (isLoading) => {
        if (confirmBtn) {
            confirmBtn.disabled = isLoading;
            confirmBtn.innerHTML = isLoading 
                ? '<span class="spinner-border spinner-border-sm"></span> 处理中...' 
                : '确认上传';
        }
    };

    /**
     * 显示状态提示
     */
    const showAlert = (type, message) => {
        if (!statusContainer) return;
        
        statusContainer.innerHTML = `
            <div class="alert alert-${type} alert-dismissible fade show">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
    };

    /**
     * 获取导入类型名称
     */
    const getImportTypeName = (type) => {
        const names = {
            [IMPORT_TYPES.STUDENT]: '学生',
            [IMPORT_TYPES.COURSE]: '课程',
            [IMPORT_TYPES.SCORE]: '成绩'
        };
        return names[type] || '数据';
    };

    return {
        init,
        openUploadModal,
        IMPORT_TYPES // 暴露常量以便外部使用
    };
})();

// 初始化示例
document.addEventListener('DOMContentLoaded', () => {
    const modalElement = document.getElementById('csv-upload-modal');
    if (modalElement) {
        const modalInstance = new bootstrap.Modal(modalElement);
        window.csvHandler.init(modalInstance);
    }
});