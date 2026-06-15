import sys
sys.path.insert(0, 'F:/mianshi_ws/study')

from app import app
from app.agents.core_planner import get_planner_response

with app.app_context():
    print('=== 直接测试 DeepSeek Planner ===')
    answer, history, steps = get_planner_response(
        '我选了哪些课，还差多少学分才能毕业？',
        context_info='当前用户学号是 20230001'
    )
    print(f'\n思考步骤数: {len(steps)}')
    for s in steps:
        t = s['type']
        c = s['content'][:100]
        print(f'[{t}] {c}')
    print(f'\n最终回答:\n{answer[:300]}')
