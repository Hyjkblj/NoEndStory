"""场景数据"""

# 场景衍生关系：每个场景可以衍生到其他相关场景
SCENE_DERIVATIONS = {
    'school': [
        'library',      # 图书馆
        'classroom',    # 教室
        'cafeteria',    # 食堂
        'playground',   # 操场
        'dormitory',    # 宿舍
        'campus_path',  # 校园小径
        'school_gate',  # 校门口
        'rooftop',      # 天台
        'gym',          # 体育馆
        'cafe_nearby'   # 学校附近的咖啡厅
    ],
    'library': [
        'school',       # 学校
        'cafe_nearby',  # 咖啡厅
        'bookstore'     # 书店
    ],
    'classroom': [
        'school',       # 学校
        'playground',  # 操场
        'cafeteria'     # 食堂
    ],
    'cafeteria': [
        'school',       # 学校
        'playground',  # 操场
        'campus_path'   # 校园小径
    ],
    'playground': [
        'school',      # 学校
        'gym',         # 体育馆
        'campus_path'   # 校园小径
    ],
    'dormitory': [
        'school',      # 学校
        'campus_path', # 校园小径
        'cafe_nearby'  # 咖啡厅
    ],
    'campus_path': [
        'school',      # 学校
        'library',     # 图书馆
        'cafe_nearby'  # 咖啡厅
    ],
    'school_gate': [
        'school',      # 学校
        'cafe_nearby', # 咖啡厅
        'bookstore'    # 书店
    ],
    'rooftop': [
        'school',      # 学校
        'classroom'    # 教室
    ],
    'gym': [
        'school',      # 学校
        'playground',  # 操场
        'cafeteria'    # 食堂
    ],
    'cafe_nearby': [
        'school',      # 学校
        'library',     # 图书馆
        'bookstore'    # 书店
    ],
    'bookstore': [
        'cafe_nearby', # 咖啡厅
        'library'      # 图书馆
    ]
}

SCENES = {
    'school': {
        'name': '学校',
        'description': '一个充满青春气息的校园场景'
    },
    'library': {
        'name': '图书馆',
        'description': '安静的学习空间，书香四溢'
    },
    'classroom': {
        'name': '教室',
        'description': '日常上课的地方，充满学习氛围'
    },
    'cafeteria': {
        'name': '食堂',
        'description': '学生们用餐的地方，热闹而温馨'
    },
    'playground': {
        'name': '操场',
        'description': '宽阔的运动场地，充满活力'
    },
    'dormitory': {
        'name': '宿舍',
        'description': '学生们的休息空间，私密而舒适'
    },
    'campus_path': {
        'name': '校园小径',
        'description': '连接校园各处的林荫小道'
    },
    'school_gate': {
        'name': '校门口',
        'description': '学校的出入口，人来人往'
    },
    'rooftop': {
        'name': '天台',
        'description': '学校建筑的顶层，视野开阔'
    },
    'gym': {
        'name': '体育馆',
        'description': '室内运动场所，设施完善'
    },
    'cafe_nearby': {
        'name': '学校附近的咖啡厅',
        'description': '温馨的咖啡厅，适合聊天和学习'
    },
    'bookstore': {
        'name': '书店',
        'description': '琳琅满目的书籍，安静而优雅'
    }
}

# 为school场景添加开头事件
SCENES['school']['opening_events'] = [
    {
        'id': 'library_meet',
        'title': '图书馆初识',
        'description': '在安静的图书馆里，你第一次注意到那个专注阅读的身影'
    },
    {
        'id': 'deskmate',
        'title': '同桌',
        'description': '新学期开始，老师安排你们成为同桌，这是你们第一次正式接触'
    },
    {
        'id': 'badminton_court',
        'title': '羽毛球场遇见',
        'description': '在学校的羽毛球场，你看到了那个挥洒汗水的身影'
    },
    {
        'id': 'cafeteria',
        'title': '食堂偶遇',
        'description': '在拥挤的食堂里，你们因为一个座位而有了第一次对话'
    },
    {
        'id': 'classroom',
        'title': '教室里的对视',
        'description': '在课堂上，你们的目光不期而遇，那一刻仿佛时间静止'
    }
]

