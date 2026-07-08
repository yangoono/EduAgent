window.dashboard = {
    init() {
        const role = window.currentUserRole || 'student';
        const sno = window.currentUserSno || '';

        // Register a premium theme color palette
        const premiumColors = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc'];

        if (role === 'student') {
            // 学生端
            const radarDom = document.getElementById('radar-chart');
            const gaugeDom = document.getElementById('gauge-chart');
            const barDom = document.getElementById('detailed-bar-chart');
            if (radarDom) charts.radar = window.echarts.init(radarDom);
            if (gaugeDom) charts.gauge = window.echarts.init(gaugeDom);
            if (barDom) charts.detailedBar = window.echarts.init(barDom);
            
            if (sno) this.loadStudentDashboard(sno, premiumColors);
        } else {
            // 教师/管理员端
            const deptDom = document.getElementById('dept-avg-chart');
            const originDom = document.getElementById('origin-chart');
            const corrDom = document.getElementById('correlation-chart');
            const pieDom = document.getElementById('pie-chart');
            const boxDom = document.getElementById('boxplot-chart');
            
            if (deptDom) charts.deptAvg = window.echarts.init(deptDom);
            if (originDom) charts.origin = window.echarts.init(originDom);
            if (corrDom) charts.correlation = window.echarts.init(corrDom);
            if (pieDom) charts.pie = window.echarts.init(pieDom);
            if (boxDom) charts.boxplot = window.echarts.init(boxDom);

            this.loadDeptAvgChart(premiumColors);
            this.loadOriginChart(premiumColors);
            this.loadCorrelationChart();
            this.populateCourseSelect(premiumColors);
            
            const distSelect = document.getElementById('course-dist-select');
            if(distSelect) {
                distSelect.addEventListener('change', (e) => this.loadCourseDistCharts(e.target.value, premiumColors));
            }
        }
    },
    async loadDeptAvgChart(colors) {
        try {
            const data = await api.get('/api/analysis/avg_score_by_dept');
            if(!charts.deptAvg) return;
            charts.deptAvg.setOption({ 
                color: colors,
                tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } }, 
                xAxis: { type: 'category', data: data.depts, axisLabel: { rotate: 30 } }, 
                yAxis: { type: 'value' }, 
                series: [{ 
                    data: data.scores, 
                    type: 'bar',
                    itemStyle: { borderRadius: [8, 8, 0, 0] }
                }] 
            });
        } catch (error) {
            console.error('Failed to load department average chart:', error);
        }
    },
    async loadOriginChart(colors) {
        try {
            const data = await api.get('/api/analysis/student_origin');
            if(!charts.origin) return;
            charts.origin.setOption({ 
                color: [colors[1]],
                tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } }, 
                xAxis: { type: 'category', data: data.hometowns, axisLabel: { rotate: 45 } }, 
                yAxis: { type: 'value' }, 
                series: [{ 
                    data: data.counts, 
                    type: 'bar',
                    itemStyle: { borderRadius: [8, 8, 0, 0] }
                }] 
            });
        } catch (error) {
            console.error('Failed to load student origin chart:', error);
        }
    },
    async loadStudentDashboard(sno, colors) {
        try {
            const data = await api.get(`/api/analysis/student_dashboard/${sno}`);
            if(!data) return;
            
            // 1. 渲染雷达图
            if(charts.radar && data.radar && data.radar.courses.length > 0) {
                charts.radar.setOption({ 
                    color: colors,
                    tooltip: { trigger: 'item' },
                    radar: { 
                        indicator: data.radar.courses.map(name => ({ name, max: 100 })),
                        splitArea: { areaStyle: { color: ['rgba(250,250,250,0.3)','rgba(200,200,200,0.1)'] } }
                    }, 
                    series: [{ 
                        type: 'radar', 
                        data: [{ 
                            value: data.radar.scores,
                            areaStyle: { color: 'rgba(84,112,198,0.4)' }
                        }] 
                    }] 
                });
            } else if (charts.radar) {
                charts.radar.setOption({ title: { text: `暂无有效成绩数据`, left: 'center', top: 'center' } });
            }

            // 2. 渲染排名与分布
            if(data.rank) {
                document.getElementById('student-dept-label').innerText = `您的专业：${data.rank.dept} | 平均成绩：${data.rank.avg_score}分`;
                document.getElementById('student-rank-display').innerText = `第 ${data.rank.rank} 名 / 共 ${data.rank.total} 人`;
                document.getElementById('student-beat-display').innerText = `击败了同专业 ${data.rank.beat_percentage}% 的同学`;
            }

            // 3. 渲染真实学业预警状态
            if(data.warning) {
                const wStatus = data.warning.status;
                const titleDom = document.getElementById('warning-title');
                const descDom = document.getElementById('warning-desc');
                const iconDom = document.getElementById('warning-icon');
                const iconContainer = document.getElementById('warning-icon-container');
                
                document.getElementById('failed-count-display').innerText = `${data.warning.failed_count} 门`;
                document.getElementById('failed-credits-display').innerText = `${data.warning.failed_credits} 学分`;

                // 移除旧颜色类
                iconContainer.className = 'p-4 rounded-circle mb-3';
                iconDom.className = 'fas';
                
                if(wStatus === 'safe') {
                    titleDom.innerText = '安全 (无学业危机)';
                    titleDom.className = 'fw-bold text-success';
                    descDom.innerText = '继续保持！目前无需学业干预。';
                    iconContainer.classList.add('bg-success', 'bg-opacity-10');
                    iconDom.classList.add('fa-check-circle', 'text-success');
                } else if(wStatus === 'yellow') {
                    titleDom.innerText = '黄色预警';
                    titleDom.className = 'fw-bold text-warning';
                    descDom.innerText = '注意：挂科已达3门或学分达10分！';
                    iconContainer.classList.add('bg-warning', 'bg-opacity-10');
                    iconDom.classList.add('fa-exclamation-circle', 'text-warning');
                } else if(wStatus === 'orange') {
                    titleDom.innerText = '橙色预警';
                    titleDom.className = 'fw-bold text-orange';
                    titleDom.style.color = '#fd7e14';
                    descDom.innerText = '危险：挂科已达4门或学分达15分！';
                    iconContainer.style.backgroundColor = 'rgba(253, 126, 20, 0.1)';
                    iconDom.classList.add('fa-exclamation-triangle');
                    iconDom.style.color = '#fd7e14';
                } else if(wStatus === 'red') {
                    titleDom.innerText = '红色预警';
                    titleDom.className = 'fw-bold text-danger';
                    descDom.innerText = '严重警告：挂科达5门或20分！';
                    iconContainer.classList.add('bg-danger', 'bg-opacity-10');
                    iconDom.classList.add('fa-radiation', 'text-danger');
                } else if(wStatus === 'expulsion') {
                    titleDom.innerText = '退学预警 (试读)';
                    titleDom.className = 'fw-bold text-dark';
                    descDom.innerText = '极度危险：挂科已达25分！';
                    iconContainer.classList.add('bg-dark', 'bg-opacity-10');
                    iconDom.classList.add('fa-skull-crossbones', 'text-dark');
                }
            }

            // 4. 渲染击败率仪表盘 (Gauge Chart)
            if(charts.gauge && data.rank) {
                charts.gauge.setOption({
                    series: [{
                        type: 'gauge',
                        startAngle: 180,
                        endAngle: 0,
                        min: 0,
                        max: 100,
                        splitNumber: 5,
                        itemStyle: {
                            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                                { offset: 0, color: '#FF6E76' },
                                { offset: 0.5, color: '#FDDD60' },
                                { offset: 1, color: '#58D9F9' }
                            ])
                        },
                        progress: { show: true, width: 18 },
                        pointer: { icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z', length: '12%', width: 20, offsetCenter: [0, '-60%'], itemStyle: { color: 'auto' } },
                        axisLine: { lineStyle: { width: 18 } },
                        axisTick: { show: false },
                        splitLine: { length: 15, lineStyle: { width: 2, color: '#999' } },
                        axisLabel: { distance: 25, color: '#999', fontSize: 14 },
                        title: { show: false },
                        detail: { valueAnimation: true, fontSize: 30, offsetCenter: [0, '20%'], formatter: '{value}%', color: 'auto' },
                        data: [{ value: data.rank.beat_percentage }]
                    }]
                });
            }

            // 5. 渲染详细成绩与学分全景柱状图 (Bar + Line)
            if(charts.detailedBar && data.radar && data.radar.courses) {
                const isFailed = (val) => val < 60;
                charts.detailedBar.setOption({
                    tooltip: { trigger: 'axis', axisPointer: { type: 'cross', crossStyle: { color: '#999' } } },
                    legend: { data: ['分数', '学分'] },
                    xAxis: [{ type: 'category', data: data.radar.courses, axisPointer: { type: 'shadow' }, axisLabel: { rotate: 30 } }],
                    yAxis: [
                        { type: 'value', name: '分数', min: 0, max: 100, interval: 20, axisLabel: { formatter: '{value} 分' } },
                        { type: 'value', name: '学分', min: 0, max: 6, interval: 1, axisLabel: { formatter: '{value} 分' } }
                    ],
                    series: [
                        { 
                            name: '分数', 
                            type: 'bar', 
                            data: data.radar.scores.map(s => ({
                                value: s,
                                itemStyle: { color: s < 60 ? '#ee6666' : '#5470c6', borderRadius: [4, 4, 0, 0] }
                            })),
                            markLine: { data: [{ yAxis: 60, name: '及格线' }], lineStyle: { color: '#ee6666' } }
                        },
                        { 
                            name: '学分', 
                            type: 'line', 
                            yAxisIndex: 1, 
                            data: data.radar.credits,
                            itemStyle: { color: '#fac858' },
                            lineStyle: { width: 3 },
                            smooth: true
                        }
                    ]
                });
            }

        } catch (error) {
            console.error(`Failed to load student dashboard for ${sno}:`, error);
        }
    },
    async loadCourseDistCharts(cno, colors) {
        try {
            const data = await api.get(`/api/analysis/course_distribution/${cno}`);
            if (data && data.pie_data && data.boxplot_data) {
                if(charts.pie) {
                    charts.pie.setOption({ 
                        color: colors,
                        tooltip: { trigger: 'item' }, 
                        series: [{ 
                            type: 'pie', 
                            radius: ['40%', '70%'], 
                            itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
                            data: data.pie_data 
                        }] 
                    });
                }
                if(charts.boxplot) {
                    charts.boxplot.setOption({ 
                        tooltip: { trigger: 'item', axisPointer: { type: 'shadow' } },
                        xAxis: { type: 'category', data: ['分数分布'] },
                        yAxis: { type: 'value', min: 0, max: 100 },
                        series: [{
                            name: 'boxplot',
                            type: 'boxplot',
                            data: [data.boxplot_data.boxData],
                            itemStyle: { color: colors[2], borderColor: colors[3] }
                        }]
                    });
                }
            }
        } catch (error) {
            console.error(`Failed to load course distribution charts for course ${cno}:`, error);
        }
    },
    async loadCorrelationChart() {
        try {
            const data = await api.get('/api/analysis/course_correlation');
            if(!charts.correlation) return;
            if(data && data.nodes && data.nodes.length > 0) {
                charts.correlation.setOption({
                    tooltip: { trigger: 'item' },
                    series: [{
                        type: 'graph',
                        layout: 'force',
                        data: data.nodes,
                        links: data.links,
                        roam: true,
                        label: { show: true, position: 'right' },
                        force: { repulsion: 300, edgeLength: 100 },
                        itemStyle: { color: '#5470c6', shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.3)' },
                        lineStyle: { color: 'source', curveness: 0.3, width: 2 }
                    }]
                });
            } else {
                charts.correlation.setOption({ title: { text: '暂无足够的及格数据产生强关联', left: 'center', top: 'center' } });
            }
        } catch (error) {
            console.error('Failed to load correlation chart:', error);
        }
    },
    async populateCourseSelect(colors) {
        try {
            const courses = await api.get('/api/courses');
            const select = document.getElementById('course-dist-select');
            if(!select) return;
            select.innerHTML = courses.map(c => `<option value="${c.cno}">${c.cname}</option>`).join('');
            if (courses.length > 0) {
                this.loadCourseDistCharts(courses[0].cno, colors);
            }
        } catch (error) {
            console.error('Failed to populate course select:', error);
        }
    }
};