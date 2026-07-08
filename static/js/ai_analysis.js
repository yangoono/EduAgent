// static/js/ai_analysis.js
window.aiAnalysisManager = {
    init() {
        // 获取页面元素的DOM引用
        const analysisTypeSelect = document.getElementById('ai-analysis-type');
        const studentSelector = document.getElementById('ai-student-selector');
        const courseSelector = document.getElementById('ai-course-selector');
        const aiStudentBtn = document.getElementById('ai-student-btn');
        const aiCourseSelect = document.getElementById('ai-course-select');
        const aiRefreshBtn = document.getElementById('ai-refresh-btn');

        this.populateCourseSelectForAI();

        // 根据分析类型切换显示学生选择器或课程选择器
        analysisTypeSelect.addEventListener('change', (e) => {
            if (e.target.value === 'student') {
                studentSelector.style.display = 'flex'; // 显示学生选择器
                courseSelector.style.display = 'none'; // 隐藏课程选择器
            } else {
                studentSelector.style.display = 'none'; // 隐藏学生选择器
                courseSelector.style.display = 'flex'; // 显示课程选择器
            }
            // 切换类型时清除之前的分析结果
            document.getElementById('ai-analysis-result').innerHTML = '<p class="text-muted text-center my-5">请选择要分析的学生或课程</p>';
        });

        // 点击学生分析按钮时触发分析
        aiStudentBtn.addEventListener('click', () => {
            const sno = document.getElementById('ai-student-input').value;
            if (sno) {
                this.getAIAnalysis('student', sno); // 获取学生分析结果
            } else {
                alert('请输入学生学号进行分析。');
            }
        });

        // 选择课程后触发课程分析
        aiCourseSelect.addEventListener('change', (e) => {
            const cno = e.target.value;
            if (cno) {
                this.getAIAnalysis('course', cno); // 获取课程分析结果
            } else {
                document.getElementById('ai-analysis-result').innerHTML = '<p class="text-muted text-center my-5">请选择要分析的课程</p>';
            }
        });

        // 点击刷新按钮时重新获取分析结果
        aiRefreshBtn.addEventListener('click', () => {
            const type = analysisTypeSelect.value;
            if (type === 'student') {
                const sno = document.getElementById('ai-student-input').value;
                if (sno) this.getAIAnalysis('student', sno);
                else alert('请输入学生学号进行分析。');
            } else if (type === 'course') {
                const cno = document.getElementById('ai-course-select').value;
                if (cno) this.getAIAnalysis('course', cno);
                else alert('请选择课程进行分析。');
            }
        });
    },

    async populateCourseSelectForAI() {
        try {
            const courses = await api.get('/api/courses');
            const select = document.getElementById('ai-course-select');
            select.innerHTML = '<option value="">选择课程</option>' + courses.map(c => `<option value="${c.cno}">${c.cname} (${c.cno})</option>`).join('');
        } catch (error) {
            console.error('加载课程数据失败:', error);
            document.getElementById('ai-course-select').innerHTML = '<option>加载课程失败</option>';
        }
    },

    async getAIAnalysis(type, id) {
        // 显示加载状态
        const resultDiv = document.getElementById('ai-analysis-result');
        resultDiv.innerHTML = '<p class="text-muted text-center my-5"><i class="fas fa-spinner fa-spin me-2"></i>正在生成分析...</p>';

        let url = '';
        if (type === 'student') {
            url = `/api/ai_analysis/student/${id}`; // 学生分析的API地址
        } else if (type === 'course') {
            url = `/api/ai_analysis/course/${id}`; // 课程分析的API地址
        }

        try {
            // 获取分析结果并显示
            const result = await api.get(url);
            if (result.success && result.analysis) {
                resultDiv.innerHTML = `<p>${result.analysis}</p>`;
            } else {
                resultDiv.innerHTML = `<p class="text-muted text-center my-5">未能获取分析结果：${result.message || '未知错误'}</p>`;
            }
        } catch (error) {
            console.error('获取AI分析结果失败:', error);
            resultDiv.innerHTML = '<p class="text-danger text-center my-5">加载AI分析时发生错误。</p>';
        }
    }
};

// 确保在DOM加载完成后初始化AI分析模块
document.addEventListener('DOMContentLoaded', () => {
    if (window.aiAnalysisManager) {
        window.aiAnalysisManager.init();
    }
});