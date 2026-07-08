// static/js/score_manager.js

document.addEventListener('DOMContentLoaded', function () {
    // 查询表单提交
    document.getElementById('score-form').addEventListener('submit', function (e) {
        e.preventDefault();
        loadScores();
    });

    // “添加成绩”按钮弹出模态框
    document.getElementById('add-score-btn').addEventListener('click', function () {
        document.getElementById('score-modal-form').reset();
        document.getElementById('score-modal-sno').readOnly = false;
        document.getElementById('score-modal-cno').disabled = false;
        document.getElementById('score-modal-form').setAttribute('data-mode', 'add');
        loadCourseOptions();
        new bootstrap.Modal(document.getElementById('score-modal')).show();
    });

    // 保存成绩按钮
    document.getElementById('save-score-btn').addEventListener('click', function () {
        const sno = document.getElementById('score-modal-sno').value.trim();
        const cno = document.getElementById('score-modal-cno').value.trim();
        const score = document.getElementById('score-modal-score').value.trim();
        const mode = document.getElementById('score-modal-form').getAttribute('data-mode');

        if (!sno || !cno || !score) {
            alert('请填写完整信息');
            return;
        }

        if (mode === 'edit') {
            // 编辑模式，调用PUT
            fetch(`/api/scores/${sno}/${cno}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ score })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    alert(data.message);
                    bootstrap.Modal.getInstance(document.getElementById('score-modal')).hide();
                    loadScores();
                } else {
                    alert(data.message);
                }
            })
            .catch(() => alert('网络错误，请重试'));
        } else {
            // 添加模式，调用POST
            fetch('/api/scores', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sno, cno, score })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    alert(data.message);
                    bootstrap.Modal.getInstance(document.getElementById('score-modal')).hide();
                    loadScores();
                } else {
                    alert(data.message);
                }
            })
            .catch(() => alert('网络错误，请重试'));
        }
    });

    // 页面加载时自动加载一次成绩
    loadScores();
});

// 加载成绩列表
function loadScores() {
    const sno = document.getElementById('score-sno').value.trim();
    const cno = document.getElementById('score-cno').value.trim();
    const range = document.getElementById('score-range').value;

    const params = new URLSearchParams();
    if (sno) params.append('student', sno);
    if (cno) params.append('course', cno);
    if (range) params.append('score', range.replace('分', ''));

    fetch('/api/scores?' + params.toString())
        .then(res => res.json())
        .then(data => renderScoreTable(data))
        .catch(() => {
            const tbody = document.getElementById('score-table-body');
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">加载失败</td></tr>';
        });
}

// 渲染成绩表格，含编辑和删除按钮
function renderScoreTable(scores) {
    const tbody = document.getElementById('score-table-body');
    tbody.innerHTML = '';
    if (!scores.length) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">暂无数据</td></tr>';
        return;
    }
    scores.forEach(item => {
        const tr = document.createElement('tr');
        let actionHtml = '';
        if (window.currentUserRole !== 'student') {
            actionHtml = `
            <td class="text-end">
                <button class="btn btn-sm btn-outline-primary me-2 edit-score-btn" data-sno="${item.sno}" data-cno="${item.cno}" data-score="${item.score}">编辑</button>
                <button class="btn btn-sm btn-outline-danger delete-score-btn" data-sno="${item.sno}" data-cno="${item.cno}">删除</button>
            </td>`;
        } else {
            actionHtml = `<td class="text-end"></td>`;
        }
        
        tr.innerHTML = `
            <td>${item.sno}</td>
            <td>${item.sname}</td>
            <td>${item.cname}</td>
            <td>${item.score}</td>
            ${actionHtml}
        `;
        tbody.appendChild(tr);
    });

    // 绑定编辑按钮事件
    document.querySelectorAll('.edit-score-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            showEditScoreModal(this.dataset.sno, this.dataset.cno, this.dataset.score);
        });
    });

    // 绑定删除按钮事件
    document.querySelectorAll('.delete-score-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            deleteScore(this.dataset.sno, this.dataset.cno);
        });
    });
}

// 编辑成绩弹窗
function showEditScoreModal(sno, cno, score) {
    document.getElementById('score-modal-sno').value = sno;
    document.getElementById('score-modal-sno').readOnly = true;
    loadCourseOptions(cno); // 选中当前课程
    document.getElementById('score-modal-cno').disabled = true;
    document.getElementById('score-modal-score').value = score;
    document.getElementById('score-modal-form').setAttribute('data-mode', 'edit');
    new bootstrap.Modal(document.getElementById('score-modal')).show();
}

// 删除成绩
function deleteScore(sno, cno) {
    if (!confirm('确定要删除这条成绩吗？')) return;
    fetch(`/api/scores/${sno}/${cno}`, { method: 'DELETE' })
        .then(res => res.json())
        .then(data => {
            alert(data.message);
            loadScores();
        })
        .catch(() => alert('网络错误，请重试'));
}

// 加载课程下拉框，支持选中
function loadCourseOptions(selectedCno) {
    fetch('/api/courses')
        .then(res => res.json())
        .then(data => {
            const select = document.getElementById('score-modal-cno');
            select.innerHTML = '';
            data.forEach(course => {
                const option = document.createElement('option');
                option.value = course.cno;
                option.textContent = `${course.cno} - ${course.cname}`;
                if (selectedCno && course.cno === selectedCno) option.selected = true;
                select.appendChild(option);
            });
        });
}