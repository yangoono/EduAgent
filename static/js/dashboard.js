window.dashboard = {
    init() {
        this.loadDeptAvgChart();
        this.loadOriginChart();
        this.populateCourseSelect();
        document.getElementById('student-radar-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault(); 
                const sno = document.getElementById('student-radar-input').value;
                if(sno) this.loadRadarChart(sno);
            }
        });
        document.getElementById('student-radar-btn').addEventListener('click', () => {
            const sno = document.getElementById('student-radar-input').value;
            if(sno) this.loadRadarChart(sno);
        });
        document.getElementById('course-dist-select').addEventListener('change', (e) => this.loadCourseDistCharts(e.target.value));
    },
    async loadDeptAvgChart() {
        try {
            const data = await api.get('/api/analysis/avg_score_by_dept');
            charts.deptAvg.setOption({ 
                title: { text: '各专业平均分' }, 
                tooltip: { trigger: 'axis' }, 
                xAxis: { type: 'category', data: data.depts, axisLabel: { rotate: 30 } }, 
                yAxis: { type: 'value' }, 
                series: [{ data: data.scores, type: 'bar' }] 
            });
        } catch (error) {
            console.error('Failed to load department average chart:', error);
            charts.deptAvg.setOption({ title: { text: '加载各专业平均分失败' } });
        }
    },
    async loadOriginChart() {
        try {
            const data = await api.get('/api/analysis/student_origin');
            charts.origin.setOption({ 
                title: { text: '学生生源地分布' }, 
                tooltip: { trigger: 'axis' }, 
                xAxis: { type: 'category', data: data.hometowns, axisLabel: { rotate: 45 } }, 
                yAxis: { type: 'value' }, 
                series: [{ data: data.counts, type: 'bar' }] 
            });
        } catch (error) {
            console.error('Failed to load student origin chart:', error);
            charts.origin.setOption({ title: { text: '加载学生生源地分布失败' } });
        }
    },
    async loadRadarChart(sno) {
        try {
            const data = await api.get(`/api/analysis/student_radar/${sno}`);
            if (data && data.courses && data.scores) {
                charts.radar.setOption({ 
                title: { text: `学生 ${sno} 成绩雷达图` }, 
                tooltip: {
                    trigger: 'item',
                    formatter: function(params) {
                        let res = '';
                        if (data.courses && data.scores) {
                            for (let i = 0; i < data.courses.length; i++) {
                                res += `${data.courses[i]}：${data.scores[i]}<br/>`;
                            }
                        }
                        return res;
                    }
                },
                radar: { indicator: data.courses.map(name => ({ name, max: 100 })) }, 
                series: [{ type: 'radar', data: [{ value: data.scores }] }] 
            });
            } else {
                charts.radar.setOption({ title: { text: `学生 ${sno} 无成绩数据` } });
            }
        } catch (error) {
            console.error(`Failed to load radar chart for student ${sno}:`, error);
            charts.radar.setOption({ title: { text: `加载学生 ${sno} 雷达图失败` } });
        }
    },
    async loadCourseDistCharts(cno) {
        try {
            const data = await api.get(`/api/analysis/course_distribution/${cno}`);
            if (data && data.pie_data && data.boxplot_data) {
                charts.pie.setOption({ 
                    title: { text: `${data.course_name} 成绩分布饼图`, left: 'center' }, 
                    tooltip: { trigger: 'item' }, 
                    series: [{ type: 'pie', radius: '50%', data: data.pie_data }] 
                });
                charts.boxplot.setOption({ 
                    title: { text: `${data.course_name} 成绩分布箱线图`, left: 'center' },
                    tooltip: {
                        trigger: 'item',
                        axisPointer: { type: 'shadow' }
                    },
                    xAxis: {
                        type: 'category',
                        data: ['成绩分布'],
                        axisLabel: { interval: 0 }
                    },
                    yAxis: {
                        type: 'value',
                        name: '分数',
                        min: 0,
                        max: 100
                    },
                    series: [{
                        name: 'boxplot',
                        type: 'boxplot',
                        data: [data.boxplot_data.boxData],
                        itemStyle: {
                            color: '#1890ff',
                            borderColor: '#096dd9'
                        }
                    }]
                });
            } else {
                charts.pie.setOption({ title: { text: `课程 ${cno} 无成绩分布数据` } });
                charts.boxplot.setOption({ title: { text: `课程 ${cno} 无成绩分布数据` } });
            }
        } catch (error) {
            console.error(`Failed to load course distribution charts for course ${cno}:`, error);
            charts.pie.setOption({ title: { text: `加载课程 ${cno} 饼图失败` } });
            charts.boxplot.setOption({ title: { text: `加载课程 ${cno} 箱线图失败` } });
        }
    },
    async populateCourseSelect() {
        try {
            const courses = await api.get('/api/courses');
            const select = document.getElementById('course-dist-select');
            select.innerHTML = courses.map(c => `<option value="${c.cno}">${c.cname}</option>`).join('');
            if (courses.length > 0) {
                this.loadCourseDistCharts(courses[0].cno);
            }
        } catch (error) {
            console.error('Failed to populate course select:', error);
            document.getElementById('course-dist-select').innerHTML = '<option>加载课程失败</option>';
        }
    }
};