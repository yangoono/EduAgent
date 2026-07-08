document.addEventListener('DOMContentLoaded', () => {
    const views = document.querySelectorAll('.main-content .view');
    const navLinks = document.querySelectorAll('.sidebar .nav-link');
    const aiAnalysisPanel = document.getElementById('ai-analysis-panel');
    const mainContentArea = document.getElementById('main-content-area');

    const exportStudentCsvBtn = document.getElementById('export-student-csv');
    const importStudentCsvBtn = document.getElementById('import-student-csv');
    const exportCourseCsvBtn = document.getElementById('export-course-csv');
    const importCourseCsvBtn = document.getElementById('import-course-csv');
    const exportScoreCsvBtn = document.getElementById('export-score-csv');
    const importScoreCsvBtn = document.getElementById('import-score-csv');

    let studentModalInstance = null;
    let courseModalInstance = null;
    let csvUploadModalInstance = null;

    window.charts = {};
    if (document.getElementById('radar-chart')) {
        window.charts.radar = echarts.init(document.getElementById('radar-chart'));
    }
    if (document.getElementById('pie-chart')) {
        window.charts.pie = echarts.init(document.getElementById('pie-chart'));
    }
    if (document.getElementById('dept-avg-chart')) {
        window.charts.deptAvg = echarts.init(document.getElementById('dept-avg-chart'));
    }
    if (document.getElementById('boxplot-chart')) {
        window.charts.boxplot = echarts.init(document.getElementById('boxplot-chart'));
    }
    if (document.getElementById('origin-chart')) {
        window.charts.origin = echarts.init(document.getElementById('origin-chart'));
    }

    window.addEventListener('resize', () => {
        for (const chartName in window.charts) {
            if (window.charts[chartName]) {
                window.charts[chartName].resize();
            }
        }
    });

    window.api = {
        get: (url) => fetch(url).then(res => {
            if (!res.ok) throw new Error(res.statusText);
            return res.json();
        }).catch(error => console.error('API GET error:', error)),
        post: (url, data) => fetch(url, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) }).then(res => {
            if (!res.ok) throw new Error(res.statusText);
            return res.json();
        }).catch(error => console.error('API POST error:', error)),
        put: (url, data) => fetch(url, { method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) }).then(res => {
            if (!res.ok) throw new Error(res.statusText);
            return res.json();
        }).catch(error => console.error('API PUT error:', error)),
        delete: (url) => fetch(url, { method: 'DELETE' }).then(res => {
            if (!res.ok) throw new Error(res.statusText);
            return res.json();
        }).catch(error => console.error('API DELETE error:', error)),
    };

    function showView(viewId) {
        views.forEach(view => {
            view.classList.remove('active');
        });
        const activeView = document.getElementById(viewId);
        if (activeView) {
            activeView.classList.add('active');
        }

        if (viewId === 'dashboard-view') {
            if (aiAnalysisPanel) {
                aiAnalysisPanel.style.display = 'block';
            }
            if (mainContentArea) {
                mainContentArea.classList.remove('col-lg-12');
                mainContentArea.classList.add('col-lg-8');
                mainContentArea.classList.add('pe-4'); 
            }
            setTimeout(() => {
                for (const chartName in window.charts) {
                    if (window.charts[chartName]) {
                        window.charts[chartName].resize();
                    }
                }
            }, 100); 
        } else {
            if (aiAnalysisPanel) {
                aiAnalysisPanel.style.display = 'none';
            }
            if (mainContentArea) {
                mainContentArea.classList.remove('col-lg-8');
                mainContentArea.classList.add('col-lg-12');
                mainContentArea.classList.remove('pe-4'); 
            }
        }
    }

    navLinks.forEach(link => {
        link.addEventListener('click', e => {
            e.preventDefault();

            navLinks.forEach(nav => nav.classList.remove('active'));
            link.classList.add('active');

            const viewId = link.dataset.view;
            showView(viewId);
        });
    });

    // --- 初始化页面加载 ---
    const dashboardLink = document.querySelector('.sidebar .nav-link[data-view="dashboard-view"]');
    if (dashboardLink) {
        dashboardLink.click();
    } else {
        console.warn("Dashboard link not found, initializing default view manually.");
        showView('dashboard-view');
    }

    // --- 初始化 Bootstrap 模态框 ---
    const studentModalEl = document.getElementById('student-modal');
    if (studentModalEl) {
        studentModalInstance = new bootstrap.Modal(studentModalEl);
    }
    const courseModalEl = document.getElementById('course-modal');
    if (courseModalEl) {
        courseModalInstance = new bootstrap.Modal(courseModalEl);
    }
    const csvUploadModalEl = document.getElementById('csv-upload-modal');
    if (csvUploadModalEl) {
        csvUploadModalInstance = new bootstrap.Modal(csvUploadModalEl);
    }

    if (importStudentCsvBtn) {
        importStudentCsvBtn.addEventListener('click', () => {
            if (csvUploadModalInstance) {
                csvUploadModalInstance.show();
                window.currentCsvImportType = 'student'; 
            }
        });
    }
    if (importCourseCsvBtn) {
        importCourseCsvBtn.addEventListener('click', () => {
            if (csvUploadModalInstance) {
                csvUploadModalInstance.show();
                window.currentCsvImportType = 'course';
            }
        });
    }
    if (importScoreCsvBtn) {
        importScoreCsvBtn.addEventListener('click', () => {
            if (csvUploadModalInstance) {
                csvUploadModalInstance.show();
                window.currentCsvImportType = 'score';
            }
        });
    }

    // --- 初始化 ---
    if (window.csvHandler && typeof window.csvHandler.init === 'function') {
        window.csvHandler.init(csvUploadModalInstance);
    }
    if (window.dashboard && typeof window.dashboard.init === 'function') {
        window.dashboard.init();
    }

    if (window.studentManager && typeof window.studentManager.init === 'function') {
        window.studentManager.init(studentModalInstance, { 
            exportBtn: exportStudentCsvBtn,
            importBtn: importStudentCsvBtn
        });
    }
    if (window.courseManager && typeof window.courseManager.init === 'function') {
        window.courseManager.init(courseModalInstance,  {
            exportBtn: exportCourseCsvBtn,
            importBtn: importCourseCsvBtn
        });
    }
    if (window.scoreManager && typeof window.scoreManager.init === 'function') {
        window.scoreManager.init(csvUploadModalInstance, {
            exportBtn: exportScoreCsvBtn,
            importBtn: importScoreCsvBtn
        });
    }
    if (window.aiAnalysis && typeof window.aiAnalysis.init === 'function') {
        window.aiAnalysis.init();
    }
});