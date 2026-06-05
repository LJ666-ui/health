"""
ZhiHealth NLP自然语言处理模块
- 中文分词（Jieba + 健康领域词典）
- 关键词提取（TF-IDF）
- 意图识别（规则+关键词权重）
- 实体提取（正则+规则匹配）
"""

import re
import jieba
import jieba.analyse
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import Counter
from loguru import logger


# ==================== 健康领域词典 ====================
HEALTH_DOMAIN_WORDS = [
    # 症状类
    "头痛", "头晕", "胸闷", "气短", "心悸", "乏力", "失眠", "多梦",
    "食欲不振", "恶心", "呕吐", "腹泻", "便秘", "腹痛", "腰酸",
    "背痛", "关节痛", "肌肉酸痛", "手脚冰凉", "出汗", "盗汗",
    "咳嗽", "咳痰", "咽痛", "鼻塞", "流涕", "耳鸣", "视力模糊",
    # 指标类
    "心率", "脉搏", "血压", "收缩压", "舒张压", "体温", "发烧",
    "血糖", "血脂", "胆固醇", "甘油三酯", "尿酸", "血红蛋白",
    "血氧", "呼吸频率", "步数", "运动量", "卡路里", "睡眠",
    "深睡", "浅睡", "REM", "体脂率", "BMI", "体重",
    # 器官/部位
    "心脏", "肝脏", "肾脏", "肺部", "胃部", "肠道", "大脑",
    "血管", "动脉", "静脉", "骨骼", "肌肉", "神经", "免疫系统",
    # 疾病类
    "高血压", "糖尿病", "冠心病", "心脏病", "中风", "脑梗",
    "肺炎", "哮喘", "胃炎", "肝炎", "肾炎", "关节炎",
    "骨质疏松", "贫血", "甲状腺", "痛风", "脂肪肝",
    # 行为/生活方式
    "饮食", "运动", "作息", "睡眠质量", "吸烟", "饮酒", "压力",
    "焦虑", "抑郁", "久坐", "熬夜", "暴饮暴食", "节食",
    # 数值描述
    "偏高", "偏低", "正常", "异常", "升高", "下降", "波动",
    "稳定", "持续", "突然", "逐渐", "剧烈", "轻微", "中度", "重度",
    # 时间相关
    "今天", "昨天", "最近", "本周", "本月", "上周", "上个月",
    "早晨", "上午", "中午", "下午", "晚上", "深夜", "凌晨",
    "每天", "经常", "偶尔", "很少", "从不",
]

# 加载自定义词典
for word in HEALTH_DOMAIN_WORDS:
    jieba.add_word(word, freq=1000)

# 停用词表（健康场景专用）
STOP_WORDS = set([
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个",
    "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好",
    "自己", "这", "那", "什么", "怎么", "如何", "为什么", "哪", "哪个", "多少",
    "请", "帮", "可以", "能", "吗", "呢", "吧", "啊", "哦", "嗯", "呀",
    "感觉", "觉得", "好像", "可能", "大概", "应该", "一般", "比较", "非常",
    "请问", "您好", "谢谢", "麻烦", "希望", "想知道", "想了解",
])


@dataclass
class Token:
    """分词结果"""
    text: str
    pos: str = ""           # 词性标注
    start: int = 0          # 起始位置
    end: int = 0            # 结束位置


@dataclass
class Entity:
    """命名实体"""
    text: str
    entity_type: str        # 实体类型: METRIC/VALUE/TIME/BODY_PART/DISEASE/ACTION
    confidence: float = 1.0
    start: int = 0
    end: int = 0
    normalized_value: Any = None   # 标准化后的值


@dataclass
class IntentResult:
    """意图识别结果"""
    intent: str             # 意图类型
    confidence: float       # 置信度
    slots: Dict[str, Any] = field(default_factory=dict)   # 提取的槽位值
    original_text: str = ""


class ChineseTokenizer:
    """中文分词器 - 基于Jieba"""

    def __init__(self, mode: str = "exact"):
        """
        Args:
            mode: 分词模式 - exact(精确)/full(全模式)/search(搜索引擎)
        """
        self.mode = mode

    def cut(self, text: str) -> List[Token]:
        """
        分词

        Args:
            text: 输入文本

        Returns:
            分词结果列表
        """
        if self.mode == "exact":
            words = jieba.lcut(text)
        elif self.mode == "full":
            words = jieba.lcut(text, cut_all=True)
        else:
            words = jieba.cut_for_search(text)

        tokens = []
        pos = 0
        for word in words:
            idx = text.find(word, pos)
            if idx == -1:
                idx = pos
            tokens.append(Token(
                text=word,
                start=idx,
                end=idx + len(word)
            ))
            pos = idx + len(word)

        return tokens

    def cut_for_search(self, text: str) -> List[str]:
        """搜索引擎模式分词（返回短词列表）"""
        return jieba.cut_for_search(text)


class KeywordExtractor:
    """关键词提取器 - 基于TF-IDF"""

    def __init__(self, top_k: int = 10):
        self.top_k = top_k

    def extract(self, text: str, with_weight: bool = False) -> List[Tuple[str, float]]:
        """
        提取关键词

        Args:
            text: 输入文本
            with_weight: 是否返回权重

        Returns:
            关键词列表 [(word, weight), ...]
        """
        try:
            keywords = jieba.analyse.extract_tags(
                text,
                topK=self.top_k,
                withWeight=with_weight,
                allowPos=('n', 'nr', 'ns', 'nt', 'nz', 'v', 'vn', 'a')
            )
            if not with_weight:
                keywords = [(kw, 1.0) for kw in keywords]
            return keywords
        except Exception as e:
            logger.warning(f"关键词提取失败: {e}")
            return []

    def extract_textrank(self, text: str, top_k: int = None) -> List[str]:
        """使用TextRank算法提取关键词"""
        k = top_k or self.top_k
        try:
            return jieba.analyse.textrank(text, topK=k)
        except Exception as e:
            logger.warning(f"TextRank提取失败: {e}")
            return []


# ==================== 意图分类体系 ====================

INTENT_DEFINITIONS = {
    "data_query": {
        "description": "数据查询 - 用户想查看健康数据记录",
        "keywords": ["查询", "看看", "显示", "数据", "记录", "历史", "最近", "多少", "数值"],
        "patterns": [
            r".*(查|看|显示|给我看看).*(心率|血压|体温|血糖|步数|睡眠|体重|数据).*(记录|历史|情况|多少|数值)",
            r".*(最近|今天|昨天|本周|本月).*(心率|血压|体温|血糖|步数|睡眠|体重).*(怎么样|是多少|如何|数据)",
            r".*(我的)?.*(心率|血压|体温|血糖|步数|睡眠|体重).*(是|有)多少",
        ],
        "slots": ["metric", "time_range"]
    },
    "health_consult": {
        "description": "健康咨询 - 关于症状、指标含义的一般性咨询",
        "keywords": ["是什么", "为什么", "怎么办", "正常吗", "好不好", "影响", "原因", "意味着"],
        "patterns": [
            r".*(正常|异常|偏高|偏低|高|低).*(吗|呢|吗\?)",
            r".*(是什么|为什么|怎么办|如何|怎样).*(心率|血压|血糖|体温|睡眠|身体)",
            r".*(是不是|是否|有没有).*(问题|危险|严重|关系|影响)",
            r".*(我|感觉|总是|经常|有时候).*(不舒服|难受|疼|痛|晕|累|困)",
        ],
        "slots": ["symptom", "concern"]
    },
    "risk_assessment": {
        "description": "风险评估 - 要求评估当前健康状况或风险等级",
        "keywords": ["风险", "评估", "分析", "判断", "预测", "预警", "健康状态", "身体状况"],
        "patterns": [
            r".*(评估|分析|判断|预测|检查).*(我的)?(健康|身体|状况|风险|状态)",
            r".*(我有|我是|属于).*(什么)?(风险|类型|等级|群体|分类)",
            r".*(帮我|给|做).*(体检|检查|评估|分析|诊断)",
        ],
        "slots": ["assessment_type", "time_scope"]
    },
    "report_generation": {
        "description": "报告生成 - 请求生成健康分析报告",
        "keywords": ["报告", "总结", "分析报告", "趋势", "解读", "周报", "月报"],
        "patterns": [
            r".*(生成|出|写|做|要).*(报告|总结|分析|解读)",
            r".*(趋势|变化|走向|发展).*(分析|解读|报告)",
            r".*(本周|本月|近期|最近).*(报告|总结|分析)",
        ],
        "slots": ["report_type", "time_range"]
    },
    "suggestion_request": {
        "description": "建议请求 - 寻求健康改善建议",
        "keywords": ["建议", "怎么", "如何改善", "该吃什么", "该怎么", "注意什么", "推荐"],
        "patterns": [
            r".*(应该|怎么|如何|需要).*(做|吃|锻炼|运动|改善|调整|注意|预防)",
            r".*(有什么|哪些).*(建议|方法|办法|方式|推荐)",
            r".*(降低|控制|改善|提高|增强|缓解).*(血压|血糖|心率|体重|睡眠|体质)",
        ],
        "slots": ["improvement_area"]
    },
    "chat_idle": {
        "description": "闲聊 - 非健康相关的对话",
        "keywords": ["你好", "谢谢", "再见", "哈哈", "无聊", "天气", " joke ", "笑话", "唱歌"],
        "patterns": [
            r"^(你好|您好|hi|hello|嗨|hey)[!！?？。]*$",
            r"^(谢谢|感谢|好的|OK|ok|嗯|哦|明白)[!！?？。]*$",
            r"^(再见|拜拜|bye)[!！?？。]*$",
        ],
        "slots": []
    }
}

# 实体提取正则规则
ENTITY_RULES = {
    "METRIC": [
        (r"(心率|脉搏)", "heart_rate"),
        (r"(收缩压|高压|舒张压|低压|血压)", "blood_pressure"),
        (r"(体温|温度|发烧|发热)", "body_temp"),
        (r"(血糖|空腹血糖|餐后血糖)", "blood_sugar"),
        (r"(血脂|胆固醇|甘油三酯)", "blood_lipid"),
        (r"(血氧|血氧饱和度)", "blood_oxygen"),
        (r"(步数|运动量|行走步数)", "steps"),
        (r"(睡眠|睡觉|睡眠时间|睡眠时长|深睡|浅睡)", "sleep"),
        (r"(体重|BMI|体脂率|体脂)", "weight"),
        (r"(呼吸频率|呼吸)", "respiratory_rate"),
    ],
    "VALUE": [
        (r"(\d+(?:\.\d+)?)\s*(mmHg|毫米汞柱)", "pressure_value"),
        (r"(\d+(?:\.\d+)?)\s*(℃|度|摄氏度)", "temp_value"),
        (r"(\d+(?:\.\d+)?)\s*(mmol/L|mol/l)", "glucose_value"),
        (r"(\d+(?:\.\d+)?)\s*(%|百分比)", "percent_value"),
        (r"(\d+(?:\.\d+)?)\s*(次[/／](分|分钟))", "rate_value"),
        (r"(\d+(?:\.\d+)?)\s*(步)", "step_value"),
        (r"(\d+(?:\.\d+)?)\s*(小时|h|hr)", "hour_value"),
        (r"(\d+(?:\.\d+)?)\s*(kg|公斤|千克)", "kg_value"),
    ],
    "TIME": [
        (r"(今天|今日|当天)", "today"),
        (r"(昨天|昨日)", "yesterday"),
        (r"(最近|近几天|这几天)", "recent_days"),
        (r"(本周|这周|这礼拜)", "this_week"),
        (r"(上周|上个星期)", "last_week"),
        (r"(本月|这个月)", "this_month"),
        (r"(最近一周|近七天|过去7天|7天内)", "last_7_days"),
        (r"(最近一月|近30天|过去30天|一个月内)", "last_30_days"),
        (r"(早晨|早上|清晨|凌晨)", "morning"),
        (r"(中午|午间)", "noon"),
        (r"(晚上|夜间|傍晚|深夜)", "evening"),
    ],
    "BODY_PART": [
        (r"(头|脑袋|头部)", "head"),
        (r"(胸|胸口|胸部)", "chest"),
        (r"(腹|肚子|腹部|胃)", "abdomen"),
        (r"(背|后背|腰部|腰)", "back"),
        (r"(手|手臂|胳膊|手指)", "hand"),
        (r"(脚|腿|腿部|膝盖|脚踝)", "leg"),
        (r"(心脏|心)", "heart_organ"),
        (r"(肺|肺部|呼吸道)", "lung"),
        (r"(肝|肝脏)", "liver"),
        (r"(肾|肾脏)", "kidney"),
    ],
    "DISEASE": [
        (r"(高血压|高血压症)", "hypertension"),
        (r"(糖尿病|高血糖)", "diabetes"),
        (r"(冠心病|心脏病|心肌缺血)", "heart_disease"),
        (r"(中风|脑卒中|脑梗|脑溢血)", "stroke"),
        (r"(感冒|流感|发热|发烧)", "cold_fever"),
        (r"(失眠|睡眠障碍|入睡困难)", "insomnia"),
        (r"(贫血|缺铁性贫血)", "anemia"),
        (r"(肥胖|超重)", "obesity"),
        (r"(骨质疏松|骨密度低)", "osteoporosis"),
        (r"(痛风|尿酸高)", "gout"),
        (r"(脂肪肝|肝脂肪)", "fatty_liver"),
    ],
}


class IntentRecognizer:
    """意图识别器 - 规则匹配 + 关键词权重"""

    def __init__(self):
        self.intents = INTENT_DEFINITIONS

    def recognize(self, text: str) -> IntentResult:
        """
        识别用户输入的意图

        Args:
            text: 用户输入文本

        Returns:
            意图识别结果
        """
        text_lower = text.lower().strip()
        scores = {}

        for intent_name, intent_def in self.intents.items():
            score = 0.0
            slots = {}

            # 1. 正则模式匹配（高权重）
            for pattern in intent_def.get("patterns", []):
                match = re.search(pattern, text_lower)
                if match:
                    score += 0.6
                    break

            # 2. 关键词匹配（中权重）
            keyword_hits = sum(
                1 for kw in intent_def.get("keywords", [])
                if kw in text_lower
            )
            keyword_score = min(keyword_hits * 0.15, 0.4)
            score += keyword_score

            # 3. 槽位提取
            for slot_name in intent_def.get("slots", []):
                slot_val = self._extract_slot(slot_name, text)
                if slot_val:
                    slots[slot_name] = slot_val

            scores[intent_name] = min(score, 1.0)

        # 选择最高分的意图
        best_intent = max(scores.items(), key=lambda x: x[1])

        return IntentResult(
            intent=best_intent[0],
            confidence=best_intent[1],
            slots=slots,
            original_text=text
        )

    def _extract_slot(self, slot_name: str, text: str) -> Optional[str]:
        """从文本中提取槽位值"""
        slot_patterns = {
            "metric": r"(心率|血压|体温|血糖|血氧|步数|睡眠|体重|血脂|BMI|体脂|呼吸)",
            "time_range": r"(今天|昨天|最近|本周|本月|上周|上个月|最近一周|最近一月|近7天|近30天|7天|30天|早晨|晚上)",
            "symptom": r"(头疼|头晕|胸闷|气短|心悸|乏力|失眠|恶心|疼痛|不舒服|难受|疼|痛|晕|累|困)",
            "assessment_type": r"(综合|整体|心血管|代谢|运动|睡眠|营养|心理)",
            "report_type": r"(趋势|综合|详细|简要|周报|月报|日报)",
            "improvement_area": r"(饮食|运动|作息|睡眠|减重|降压|控糖|戒烟|戒酒|减压|心态)",
            "concern": r"(正常|异常|危险|严重|有问题|有问题吗|有关系|影响)",
            "time_scope": r"(短期|中期|长期|当前|未来|历史|近期)",
        }

        pattern = slot_patterns.get(slot_name)
        if pattern:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None


class EntityExtractor:
    """命名实体提取器 - 正则 + 规则匹配"""

    def __init__(self):
        self.rules = ENTITY_RULES

    def extract(self, text: str) -> List[Entity]:
        """
        从文本中提取所有命名实体

        Args:
            text: 输入文本

        Returns:
            实体列表
        """
        entities = []

        for entity_type, rules in self.rules.items():
            for pattern, normalized in rules:
                for match in re.finditer(pattern, text):
                    entities.append(Entity(
                        text=match.group(),
                        entity_type=entity_type,
                        confidence=0.9,
                        start=match.start(),
                        end=match.end(),
                        normalized_value=normalized
                    ))

        # 按位置排序
        entities.sort(key=lambda e: e.start)
        return entities

    def extract_by_type(self, text: str, entity_type: str) -> List[Entity]:
        """按类型提取实体"""
        return [e for e in self.extract(text) if e.entity_type == entity_type]


class NLPProcessor:
    """NLP处理器 - 统一入口"""

    def __init__(self):
        self.tokenizer = ChineseTokenizer(mode="exact")
        self.keyword_extractor = KeywordExtractor(top_k=10)
        self.intent_recognizer = IntentRecognizer()
        self.entity_extractor = EntityExtractor()

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        全面的NLP分析（一次性完成分词/关键词/意图/实体）

        Args:
            text: 用户输入文本

        Returns:
            完整的分析结果字典
        """
        result = {
            "original_text": text,
            "tokens": [t.text for t in self.tokenizer.cut(text)],
            "token_count": 0,
            "keywords": [],
            "intent": None,
            "entities": []
        }

        # 1. 分词
        tokens = self.tokenizer.cut(text)
        result["tokens"] = [t.text for t in tokens]
        result["token_count"] = len(tokens)

        # 2. 关键词提取
        kws = self.keyword_extractor.extract(text, with_weight=True)
        result["keywords"] = [{"word": w, "weight": round(s, 4)} for w, s in kws]

        # 3. 意图识别
        intent_result = self.intent_recognizer.recognize(text)
        result["intent"] = {
            "type": intent_result.intent,
            "confidence": round(intent_result.confidence, 4),
            "description": INTENT_DEFINITIONS.get(intent_result.intent, {}).get("description", ""),
            "slots": intent_result.slots
        }

        # 4. 实体提取
        entities = self.entity_extractor.extract(text)
        result["entities"] = [
            {
                "text": e.text,
                "type": e.entity_type,
                "normalized": e.normalized_value,
                "confidence": e.confidence
            }
            for e in entities
        ]

        logger.info(f"NLP分析完成: intent={intent_result.intent}, "
                     f"confidence={intent_result.confidence:.2f}, "
                     f"entities={len(entities)}, tokens={len(tokens)}")

        return result


# ==================== Flask接口封装 ====================

def create_nlp_api(app=None):
    """创建NLP API路由（挂载到Flask app）"""
    from flask import request, jsonify

    processor = NLPProcessor()

    @app.route('/api/nlp/analyze', methods=['POST'])
    def analyze_text():
        """完整NLP分析接口"""
        data = request.get_json()
        text = data.get("text", "")

        if not text or len(text.strip()) == 0:
            return jsonify({"code": 400, "success": False, "message": "文本不能为空"}), 400

        result = processor.analyze(text)
        return jsonify({"code": 200, "success": True, "data": result})

    @app.route('/api/nlp/tokenize', methods=['POST'])
    def tokenize():
        """分词接口"""
        data = request.get_json()
        text = data.get("text", "")
        mode = data.get("mode", "exact")

        tokenizer = ChineseTokenizer(mode=mode)
        tokens = tokenizer.cut(text)

        return jsonify({
            "code": 200,
            "success": True,
            "data": {"tokens": [t.text for t in tokens], "count": len(tokens)}
        })

    @app.route('/api/nlp/keywords', methods=['POST'])
    def extract_keywords():
        """关键词提取接口"""
        data = request.get_json()
        text = data.get("text", "")
        top_k = data.get("top_k", 10)

        extractor = KeywordExtractor(top_k=top_k)
        keywords = extractor.extract(text, with_weight=True)

        return jsonify({
            "code": 200,
            "success": True,
            "data": [{"word": w, "weight": round(s, 4)} for w, s in keywords]
        })

    @app.route('/api/nlp/intent', methods=['POST'])
    def recognize_intent():
        """意图识别接口"""
        data = request.get_json()
        text = data.get("text", "")

        recognizer = IntentRecognizer()
        result = recognizer.recognize(text)

        return jsonify({
            "code": 200,
            "success": True,
            "data": {
                "intent": result.intent,
                "confidence": round(result.confidence, 4),
                "description": INTENT_DEFINITIONS.get(result.intent, {}).get("description", ""),
                "slots": result.slots
            }
        })

    @app.route('/api/nlp/entities', methods=['POST'])
    def extract_entities():
        """实体提取接口"""
        data = request.get_json()
        text = data.get("text", "")
        entity_type = data.get("type")  # 可选，按类型过滤

        extractor = EntityExtractor()

        if entity_type:
            entities = extractor.extract_by_type(text, entity_type)
        else:
            entities = extractor.extract(text)

        return jsonify({
            "code": 200,
            "success": True,
            "data": [
                {"text": e.text, "type": e.entity_type, "normalized": e.normalized_value}
                for e in entities
            ]
        })

    logger.info("[NLP] API路由注册完成")
    return app
