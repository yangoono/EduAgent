// static/js/student_manager.js

window.studentManager = {
    modalInstance: null, // 学生编辑/添加 模态框
    // DOM引用
    exportButton: null,  
    importButton: null,  
    studentSearchForm: null, 
    studentSearchInput: null, 
    studentSearchDept: null, 
    studentSearchGrade: null, 
    studentSearchClass: null,
    allStudentsData: [], 

    /**
     * 初始化学生管理模块
     * 在页面加载时调用，用于设置所有必要的事件监听器和初始数据加载
     * @param {object} modal 学生编辑/添加模态框的 Bootstrap 实例
     * @param {object} buttons 包含导出和导入按钮 DOM 引用的对象
     */
    init(modal, buttons) {
        this.modalInstance = modal;
        this.exportButton = buttons.exportBtn;
        this.importButton = buttons.importBtn;

        // 获取所有搜索和筛选元素的 DOM 引用
        this.studentSearchForm = document.getElementById('student-search-form');
        this.studentSearchInput = document.getElementById('student-search-input');
        this.studentSearchDept = document.getElementById('student-search-dept');
        this.studentSearchGrade = document.getElementById('student-search-grade'); 
        this.studentSearchClass = document.getElementById('student-search-class'); 

        this.loadStudents();

        // 为“添加学生”按钮绑定点击事件
        document.getElementById('add-student-btn').addEventListener('click', () => this.showModal());
        // 为模态框中的“保存学生”按钮绑定点击事件
        document.getElementById('save-student-btn').addEventListener('click', () => this.saveStudent());

        // 为“导出CSV”按钮绑定点击事件
        if (this.exportButton) {
            this.exportButton.addEventListener('click', () => this.exportStudentsCsv());
            console.log("学生导出CSV按钮点击事件已绑定。");
        } else {
            console.warn("导出按钮在 student_manager.js 初始化阶段为 null 或 undefined。");
        }

        // 为“导入CSV”按钮绑定点击事件 (假设 csv_handler.js 会处理模态框)
        if (this.importButton) {
            this.importButton.addEventListener('click', () => {
                // 假设 window.csvHandler 暴露了一个方法来打开上传模态框并处理特定类型
                window.csvHandler.openUploadModal('students');
                console.log("学生导入CSV按钮点击事件已绑定。");
            });
        } else {
            console.warn("导入按钮在 student_manager.js 初始化阶段为 null 或 undefined。");
        }

        // 为查询表单绑定提交事件，阻止默认刷新行为并触发筛选
        if (this.studentSearchForm) {
            this.studentSearchForm.addEventListener('submit', (e) => {
                e.preventDefault(); // 阻止表单的默认提交行为（页面重新加载）
                this.filterStudents(); // 触发筛选
            });
            console.log("学生查询表单提交事件已绑定。");
        }

        // 监听专业筛选下拉框的变化，触发筛选
        if (this.studentSearchDept) {
            this.studentSearchDept.addEventListener('change', () => this.filterStudents());
            console.log("学生专业筛选下拉框 change 事件已绑定。");
        }
    },

    /**
     * 异步加载学生数据并渲染表格。
     * 此函数也在操作（如添加、编辑、删除）后或初始加载时调用，用于刷新数据。
     */
    async loadStudents() {
        try {
            const students = await api.get('/api/students');
            this.allStudentsData = students; // 将所有学生数据存储在本地
            this.renderStudentTable(students); // 初始加载时渲染所有学生数据
            this.populateDepartmentFilter(students); // 仅填充专业筛选器（年级和班级现在是输入框）
        } catch (error) {
            console.error('加载学生数据失败:', error);
            document.getElementById('student-table-body').innerHTML = '<tr><td colspan="7" class="text-center">加载学生数据失败。</td></tr>';
        }
    },

    /**
     * 根据当前的搜索输入和下拉菜单选择项来过滤学生数据，然后渲染表格。
     */
    filterStudents() {
        const searchText = this.studentSearchInput.value.toLowerCase().trim();
        const selectedDept = this.studentSearchDept.value;
        const inputGrade = this.studentSearchGrade.value.toLowerCase().trim(); // 获取年级输入框的值
        const inputClass = this.studentSearchClass.value.toLowerCase().trim(); // 获取班级输入框的值

        const filteredStudents = this.allStudentsData.filter(s => {
            // 检查学号或姓名是否匹配搜索文本
            const matchesText = !searchText || 
                              s.sno.toLowerCase().includes(searchText) || 
                              s.sname.toLowerCase().includes(searchText);
            // 检查专业是否匹配选定专业
            const matchesDept = !selectedDept || s.sdept === selectedDept;
            
            const sno = s.sno || '';
            const sclass = sno;

            // 处理年级输入
            let gradeInput = inputGrade.trim();
            if (gradeInput.length === 4 && /^\d{4}$/.test(gradeInput)) {
                gradeInput = gradeInput.substring(2, 4); // 取后两位
            }

            // sno 前两位
            const sgrade = sno.substring(0, 2);

            // 前缀匹配
            const matchesGrade = !gradeInput || sgrade === gradeInput;
            const matchesClass = !inputClass || sclass.startsWith(inputClass);
            
            // 所有条件都必须满足才能通过筛选
            return matchesText && matchesDept && matchesGrade && matchesClass;
        });

        this.renderStudentTable(filteredStudents);
    },

    /**
     * 使用提供的学生数组渲染学生表格。
     * @param {Array} studentsToRender 要显示的学生对象数组。
     */
    renderStudentTable(studentsToRender) {
        const tbody = document.getElementById('student-table-body');
        if (studentsToRender.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center">没有找到匹配的学生数据。</td></tr>';
            return;
        }

        // 将学生数据映射为 HTML 表格行并添加到 tbody
        tbody.innerHTML = studentsToRender.map(s => `
            <tr data-sno="${s.sno}">
                <td>${s.sno}</td>
                <td>${s.sname}</td>
                <td>${s.ssex}</td>
                <td>${s.sage}</td>
                <td>${s.sdept}</td>
                <td>${s.hometown}</td>
                <td class="text-end">
                    <button class="btn btn-sm btn-outline-primary edit-student-btn">编辑</button>
                    <button class="btn btn-sm btn-outline-danger delete-student-btn">删除</button>
                </td>
            </tr>
        `).join('');
        this.addTableListeners(); // 为新渲染的按钮添加事件监听器
    },

    /**
     * 仅填充专业筛选下拉菜单。年级和班级现在是输入框，无需动态填充。
     * @param {Array} students 可选：用于提取唯一值的学生对象数组。
     */
    populateDepartmentFilter(students = this.allStudentsData) {
        const deptSelect = this.studentSearchDept;
        deptSelect.innerHTML = '<option value="">所有专业</option>'; // 保留“所有专业”选项
        const departments = new Set();
        students.forEach(s => { if (s.sdept) departments.add(s.sdept); });
        Array.from(departments).sort().forEach(dept => {
            const option = document.createElement('option');
            option.value = dept;
            option.textContent = dept;
            deptSelect.appendChild(option);
        });
        // 年级和班级现在是输入框，无需填充
    },

    /**
     * 为表格中的编辑和删除按钮添加事件监听器。
     */
    addTableListeners() {
        document.querySelectorAll('.edit-student-btn').forEach(btn => 
            btn.addEventListener('click', e => this.showModal(e.target.closest('tr').dataset.sno))
        );
        document.querySelectorAll('.delete-student-btn').forEach(btn => 
            btn.addEventListener('click', e => {
                const sno = e.target.closest('tr').dataset.sno;
                if (confirm(`确定删除学号为 ${sno} 的学生吗？这将同时删除该学生的所有成绩记录！`)) {
                    this.deleteStudent(sno);
                }
            })
        );
    },

    /**
     * 显示学生编辑/添加模态框。
     * @param {string|null} sno 如果是编辑模式，则传入学生学号；如果是添加模式，则为 null。
     */
    showModal(sno = null) {
        const form = document.getElementById('student-form');
        form.reset(); // 重置表单内容

        document.getElementById('student-modal-title').textContent = sno ? '编辑学生' : '添加学生';
        // 在编辑模式下禁用学号输入框，因为学号通常作为主键不应被修改
        document.getElementById('student-sno').disabled = !!sno; 

        if (sno) { // 如果是编辑模式，填充表单
            const student = this.allStudentsData.find(s => s.sno === sno);
            if (student) {
                document.getElementById('student-sno-hidden').value = sno; // 隐藏域存储原始学号
                document.getElementById('student-sno').value = student.sno;
                document.getElementById('student-sname').value = student.sname;
                document.getElementById('student-ssex').value = student.ssex;
                document.getElementById('student-sage').value = student.sage;
                document.getElementById('student-sdept').value = student.sdept;
                document.getElementById('student-hometown').value = student.hometown;
            }
        } else { 
            document.getElementById('student-sno-hidden').value = ''; 
        }
        this.modalInstance.show();
    },

    /**
     * 保存学生数据（添加或更新）。
     */
    async saveStudent() {
        const sno_hidden = document.getElementById('student-sno-hidden').value;
        const isEdit = !!sno_hidden; // 根据隐藏域是否有值判断是否为编辑操作

        const studentData = {
            sno: document.getElementById('student-sno').value,
            sname: document.getElementById('student-sname').value,
            ssex: document.getElementById('student-ssex').value,
            sage: parseInt(document.getElementById('student-sage').value),
            sdept: document.getElementById('student-sdept').value,
            hometown: document.getElementById('student-hometown').value
        };

        if (!studentData.sno || !studentData.sname || !studentData.sdept || isNaN(studentData.sage)) {
            alert('请填写所有必填的学生信息（学号、姓名、专业、年龄）。');
            return;
        }

        try {
            const result = isEdit 
                ? await api.put(`/api/students/${sno_hidden}`, studentData) 
                : await api.post('/api/students', studentData);
            
            if (result.success) {
                this.modalInstance.hide(); // 隐藏模态框
                await this.loadStudents(); // 重新加载学生表格数据并刷新筛选器
                
                // 如果其他模块依赖学生数据，也进行刷新
                if (window.scoreManager) await window.scoreManager.populateSelects(); // 刷新成绩表单的学生下拉列表
                if (window.dashboard) await window.dashboard.loadDeptAvgChart(); // 刷新仪表盘图表
                alert(isEdit ? '学生信息更新成功！' : '学生添加成功！'); // 弹出成功提示
            } else {
                alert(`操作失败: ${result.message}`); // 弹出操作失败提示
            }
        } catch (error) {
            console.error('保存学生信息时出错:', error);
            alert('保存学生信息时发生错误。');
        }
    },

    /**
     * 删除学生。
     * @param {string} sno 要删除学生的学号。
     */
    async deleteStudent(sno) {
        try {
            const result = await api.delete(`/api/students/${sno}`);
            if (result.success) {
                await this.loadStudents(); // 重新加载学生表格数据并刷新筛选器
                // 刷新其他依赖学生数据的模块
                if (window.scoreManager) await window.scoreManager.populateSelects();
                if (window.dashboard) await window.dashboard.loadDeptAvgChart();
                alert('学生删除成功！'); // 弹出删除成功提示
            } else {
                alert(`删除失败: ${result.message}`); // 弹出删除失败提示
            }
        } catch (error) {
            console.error('删除学生时出错:', error);
            alert('删除学生时发生错误。');
        }
    },

    /**
     * 处理学生数据导出为CSV文件，根据当前的筛选条件。
     */
    async exportStudentsCsv() {
        console.log("exportStudentsCsv 方法被成功调用！");

        // 获取当前的筛选值
        const searchText = this.studentSearchInput.value.trim();
        const selectedDept = this.studentSearchDept.value;
        const inputGrade = this.studentSearchGrade.value.trim(); // 获取年级输入框的值
        const inputClass = this.studentSearchClass.value.trim(); // 获取班级输入框的值

        // 构建查询参数对象
        const params = new URLSearchParams();
        if (searchText) {
            params.append('searchText', searchText);
        }
        if (selectedDept) {
            params.append('sdept', selectedDept);
        }
        if (inputGrade) { // 如果输入了年级，添加到参数中
            params.append('sgrade', inputGrade); // 使用 'sgrade' 作为后端参数名
        }
        if (inputClass) { // 如果输入了班级，添加到参数中
            params.append('sclass', inputClass); // 使用 'sclass' 作为后端参数名
        }

        // 构建带查询参数的 URL
        const url = `/api/students/export-csv?${params.toString()}`;

        try {
            // 向后端 API 发起 GET 请求获取 CSV 数据，包含筛选参数
            const response = await fetch(url);

            if (!response.ok) {
                // 如果后端返回 404，可能是没有匹配的数据
                if (response.status === 404) {
                    alert('没有找到匹配的学生数据可供导出。');
                    return;
                }
                const errorData = await response.json(); // 尝试解析 JSON 格式的错误响应
                throw new Error(`服务器错误: ${response.status} - ${errorData.message || '未知错误'}`);
            }

            const blob = await response.blob(); // 获取响应的二进制数据 (Blob 对象)
            const downloadUrl = window.URL.createObjectURL(blob); // 为 Blob 对象创建一个临时 URL，用于下载

            // 创建一个隐藏的 <a> 标签来触发文件下载
            const a = document.createElement('a');
            a.style.display = 'none'; // 隐藏链接元素
            a.href = downloadUrl; // 设置下载链接
            a.download = 'students.csv'; // 设置下载文件的默认名称

            // 将链接添加到文档体中并模拟点击，从而触发下载
            document.body.appendChild(a);
            a.click();

            // 清理：移除临时创建的 <a> 标签并释放 Blob URL，防止内存泄漏
            document.body.removeChild(a); 
            window.URL.revokeObjectURL(downloadUrl);

            alert('学生数据导出成功！');
        } catch (error) {
            console.error('导出学生数据CSV失败:', error);
            alert('导出学生数据失败: ' + error.message);
        }
    }
};