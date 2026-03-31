"""
同龄人化表达服务 - 校园场景专用语料库和提示词模板
实现Z世代用户群体的自然、亲切对话风格
"""
import json
import random
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class ExpressionStyle(str, Enum):
    """表达风格类型"""
    CASUAL = "casual"  #  casual随意
    ENERGETIC = "energetic"  #  energetic活泼
    GENTLE = "gentle"  #  gentle温柔
    HUMOROUS = "humorous"  #  humorous幽默
    ENCOURAGING = "encouraging"  #  encouraging鼓励


class ScenarioType(str, Enum):
    """场景类型"""
    RECORD_SUCCESS = "record_success"  # 记账成功
    BUDGET_WARNING = "budget_warning"  # 预算预警
    BUDGET_EXCEEDED = "budget_exceeded"  # 超支提醒
    DAILY_REPORT = "daily_report"  # 日报
    WEEKLY_REPORT = "weekly_report"  # 周报
    MONTHLY_REPORT = "monthly_report"  # 月报
    SAVING_ACHIEVEMENT = "saving_achievement"  # 省钱成就
    EXPENSIVE_REMINDER = "expensive_reminder"  # 大额提醒
    CLARIFICATION = "clarification"  # 澄清询问
    GREETING = "greeting"  # 问候
    FAREWELL = "farewell"  # 告别
    ERROR = "error"  # 错误提示


@dataclass
class ExpressionTemplate:
    """表达模板"""
    style: ExpressionStyle
    scenario: ScenarioType
    templates: List[str]
    emoji_pool: List[str]
    tone_description: str


class PeerExpressionService:
    """同龄人化表达服务"""
    
    def __init__(self):
        self.templates = self._init_templates()
        self.vocabulary = self._init_vocabulary()
        self.scenario_contexts = self._init_scenario_contexts()
    
    def _init_templates(self) -> Dict[ScenarioType, List[ExpressionTemplate]]:
        """初始化表达模板库"""
        return {
            ScenarioType.RECORD_SUCCESS: [
                ExpressionTemplate(
                    style=ExpressionStyle.CASUAL,
                    scenario=ScenarioType.RECORD_SUCCESS,
                    templates=[
                        "okk，{amount}元的{category}已记好啦 ✓",
                        "收到！{category}花了{amount}元，已存档 📋",
                        "记下了记下了，{amount}块的{category} ✨",
                        "搞定！{category}支出{amount}元已记录 📝",
                        "好嘞，{amount}元的{category}帮你记上啦 👌"
                    ],
                    emoji_pool=["✓", "📋", "✨", "📝", "👌", "💰", "✅"],
                    tone_description="轻松随意，像朋友聊天"
                ),
                ExpressionTemplate(
                    style=ExpressionStyle.ENERGETIC,
                    scenario=ScenarioType.RECORD_SUCCESS,
                    templates=[
                        "哇！{category}花了{amount}元，记账小能手上线 💪",
                        "棒棒哒！{amount}元的{category}记录成功 🎉",
                        "记账成功！{category}支出{amount}元，继续保持 🌟",
                        "太棒了！{amount}块的{category}已入账，理财小达人就是你 🏆",
                        "nice！{category}花了{amount}元，记录完毕 ✨"
                    ],
                    emoji_pool=["💪", "🎉", "🌟", "🏆", "✨", "🚀", "💯"],
                    tone_description="热情鼓励，正能量满满"
                ),
                ExpressionTemplate(
                    style=ExpressionStyle.HUMOROUS,
                    scenario=ScenarioType.RECORD_SUCCESS,
                    templates=[
                        "钱包-1，记录+1，{amount}元的{category}已入库 😂",
                        "又一笔{category}支出{amount}元，钱包在哭泣 💸",
                        "{amount}块{category}已记录，钱钱飞走了～ 💨",
                        "记账成功！{category}花了{amount}，离暴富又远了一步 😅",
                        "{amount}元的{category}已存档，今天的消费KPI完成 📊"
                    ],
                    emoji_pool=["😂", "💸", "💨", "😅", "📊", "🤣", "😆"],
                    tone_description="幽默调侃，轻松化解消费焦虑"
                )
            ],
            
            ScenarioType.BUDGET_WARNING: [
                ExpressionTemplate(
                    style=ExpressionStyle.GENTLE,
                    scenario=ScenarioType.BUDGET_WARNING,
                    templates=[
                        "宝，{category}预算已经用了{percentage}%啦，注意控制一下哦 ⚠️",
                        "提醒一下，{category}这个月花了{percentage}%的预算，要留意一下 👀",
                        "{category}预算进度{percentage}%了，可以适当规划一下剩余部分 📅",
                        "温馨提示：{category}已用{percentage}%，还有{remaining}元额度 💳",
                        "{category}预算使用{percentage}%啦，要不要考虑稍微节省一点？🤔"
                    ],
                    emoji_pool=["⚠️", "👀", "📅", "💳", "🤔", "💡", "🌸"],
                    tone_description="温柔提醒，不带指责"
                ),
                ExpressionTemplate(
                    style=ExpressionStyle.ENCOURAGING,
                    scenario=ScenarioType.BUDGET_WARNING,
                    templates=[
                        "{category}用了{percentage}%，还有空间！相信你能规划好 💪",
                        "预算进度{percentage}%，剩下的{remaining}元可以精打细算 ✨",
                        "{category}已用{percentage}%，加油！理性消费你最棒 🌟",
                        "还有{remaining}元{category}预算，合理分配完全OK 👍",
                        "{percentage}%进度达成！剩下的预算可以创造更多价值 🎯"
                    ],
                    emoji_pool=["💪", "✨", "🌟", "👍", "🎯", "🔥", "💯"],
                    tone_description="积极鼓励，强调剩余空间"
                )
            ],
            
            ScenarioType.BUDGET_EXCEEDED: [
                ExpressionTemplate(
                    style=ExpressionStyle.GENTLE,
                    scenario=ScenarioType.BUDGET_EXCEEDED,
                    templates=[
                        "{category}预算超了{exceeded}元，没关系，下个月调整一下就好 🌱",
                        "超支提醒：{category}多花了{exceeded}元，别焦虑，复盘一下原因 📊",
                        "{category}这个月超了{exceeded}元，抱抱你，下次注意就好 🤗",
                        "预算告急：{category}超支{exceeded}元，不过偶尔放纵一下也正常 💝",
                        "{category}超了{exceeded}元，没关系，记账就是为了了解自己的消费习惯 💡"
                    ],
                    emoji_pool=["🌱", "📊", "🤗", "💝", "💡", "🌸", "💪"],
                    tone_description="安慰理解，减轻焦虑"
                ),
                ExpressionTemplate(
                    style=ExpressionStyle.HUMOROUS,
                    scenario=ScenarioType.BUDGET_EXCEEDED,
                    templates=[
                        "{category}预算：我裂开了 💔 超了{exceeded}元",
                        "钱包：我太难了 😭 {category}超支{exceeded}元",
                        "{category}预算已阵亡，超额{exceeded}元，下个月再战！🚀",
                        "超支{exceeded}元，{category}这波操作有点秀 😅",
                        "{category}：预算是什么？能吃吗？超了{exceeded}元 🤣"
                    ],
                    emoji_pool=["💔", "😭", "🚀", "😅", "🤣", "😂", "💸"],
                    tone_description="幽默化解，不制造压力"
                )
            ],
            
            ScenarioType.DAILY_REPORT: [
                ExpressionTemplate(
                    style=ExpressionStyle.CASUAL,
                    scenario=ScenarioType.DAILY_REPORT,
                    templates=[
                        "今日账单来啦！总共花了{total}元，{top_category}占了大头 📱",
                        "今天消费{total}元，主要是{top_category}，还算正常范围 👌",
                        "日报：支出{total}元，{top_category}花了{top_amount}元，其他还好 📋",
                        "今天花了{total}块，{top_category}是主要开销，记得复盘哦 ✨",
                        "消费总结：今日{total}元，{top_category}占比最高，明天继续观察 👀"
                    ],
                    emoji_pool=["📱", "👌", "📋", "✨", "👀", "📊", "💰"],
                    tone_description="日常分享，像朋友汇报"
                )
            ],
            
            ScenarioType.WEEKLY_REPORT: [
                ExpressionTemplate(
                    style=ExpressionStyle.ENCOURAGING,
                    scenario=ScenarioType.WEEKLY_REPORT,
                    templates=[
                        "本周消费{total}元，比上周{comparison}{diff}元，{trend}！🎉",
                        "周报出炉！花了{total}元，{trend}趋势，继续保持 💪",
                        "这周账单：{total}元，{top_category}是主力消费，整体{trend} 📈",
                        "7天消费{total}元，{trend}了{diff}元，理财小达人就是你 🌟",
                        "本周总结：{total}元支出，{trend}明显，下周继续加油 🚀"
                    ],
                    emoji_pool=["🎉", "💪", "📈", "🌟", "🚀", "📊", "✨"],
                    tone_description="积极正向，鼓励为主"
                )
            ],
            
            ScenarioType.SAVING_ACHIEVEMENT: [
                ExpressionTemplate(
                    style=ExpressionStyle.ENERGETIC,
                    scenario=ScenarioType.SAVING_ACHIEVEMENT,
                    templates=[
                        "太厉害了！这个月省了{amount}元，存钱小能手非你莫属 🏆",
                        "恭喜恭喜！预算内省了{amount}元，可以奖励自己一杯奶茶 🧋",
                        "哇！{amount}元结余，理财能力MAX！继续保持 💯",
                        "省钱成功！{amount}元存下，离小目标又近了一步 🎯",
                        "棒棒哒！{amount}元结余，理性消费典范，给你点赞 👍"
                    ],
                    emoji_pool=["🏆", "🧋", "💯", "🎯", "👍", "🎉", "💰"],
                    tone_description="热烈祝贺，强化成就感"
                )
            ],
            
            ScenarioType.EXPENSIVE_REMINDER: [
                ExpressionTemplate(
                    style=ExpressionStyle.GENTLE,
                    scenario=ScenarioType.EXPENSIVE_REMINDER,
                    templates=[
                        "这笔{category}花了{amount}元，金额有点大，确认一下是不是必要支出？🤔",
                        "{amount}元的{category}，属于大额消费，建议考虑一下再决定 💭",
                        "大额提醒：{category}支出{amount}元，确定要记录吗？👀",
                        "{amount}块{category}，比平时高不少，确认无误我就记下啦 ✋",
                        "这笔{category}{amount}元，建议三思，确定要入账单吗？🤔"
                    ],
                    emoji_pool=["🤔", "💭", "👀", "✋", "⚠️", "💡", "🌸"],
                    tone_description="善意提醒，不带评判"
                )
            ],
            
            ScenarioType.CLARIFICATION: [
                ExpressionTemplate(
                    style=ExpressionStyle.CASUAL,
                    scenario=ScenarioType.CLARIFICATION,
                    templates=[
                        "emmm，没太get到，这笔支出具体是多少钱呀？🤔",
                        "等等，金额部分我没听清，能再说一下吗？👂",
                        "{category}我懂，但是花了多少来着？😅",
                        "信息有点模糊，能补充一下金额吗？💭",
                        "大概懂了，但是具体数字是多少呀？📝"
                    ],
                    emoji_pool=["🤔", "👂", "😅", "💭", "📝", "❓", "💡"],
                    tone_description="自然询问，不尴尬"
                )
            ],
            
            ScenarioType.GREETING: [
                ExpressionTemplate(
                    style=ExpressionStyle.ENERGETIC,
                    scenario=ScenarioType.GREETING,
                    templates=[
                        "嗨！今天也要好好记账哦 ✨",
                        "哈喽！准备好记录今天的支出了吗？📝",
                        "Hey！又是元气满满的一天，开始记账吧 💪",
                        "Hi！今天消费情况如何？来记录一下吧 👋",
                        "你好呀！记账小助手上线，随时为你服务 🌟"
                    ],
                    emoji_pool=["✨", "📝", "💪", "👋", "🌟", "🎉", "☀️"],
                    tone_description="热情友好，拉近距离"
                )
            ],
            
            ScenarioType.ERROR: [
                ExpressionTemplate(
                    style=ExpressionStyle.GENTLE,
                    scenario=ScenarioType.ERROR,
                    templates=[
                        "哎呀，出了点小问题，稍后再试一下吧 🙏",
                        "抱歉，刚才没处理好，能再说一遍吗？😅",
                        "系统开小差了，重新试一次应该就好了 🔄",
                        "抱歉抱歉，刚才走神了，能再输入一次吗？🙇",
                        "出了点bug，程序员正在疯狂修复中 🐛"
                    ],
                    emoji_pool=["🙏", "😅", "🔄", "🙇", "🐛", "💦", "🌸"],
                    tone_description="诚恳道歉，不甩锅"
                )
            ]
        }
    
    def _init_vocabulary(self) -> Dict[str, List[str]]:
        """初始化同龄人词汇库"""
        return {
            "positive_adjectives": [
                "棒", "nice", "优秀", "给力", "靠谱", "绝了", "yyds", "神仙",
                "宝藏", "真香", "奥利给", "冲鸭", "666", "牛", "强", "赞"
            ],
            "encouraging_words": [
                "加油", "可以的", "没问题", "相信你能行", "你超棒的",
                "继续保持", "稳", "拿捏住了", "有内味儿了", "拿捏"
            ],
            "casual_fillers": [
                "emm", "那个", "就是", "其实", "话说", "讲道理", "有一说一",
                "u1s1", "实不相瞒", "说实话", "讲真"
            ],
            "emotional_expressions": [
                "芜湖", "绝了", "笑死", "破防了", "emo了", "躺平", "摆烂",
                "卷起来了", "真不错", "我哭了", "我酸了"
            ],
            "internet_slang": [
                "get", "打工人", "干饭人", "尾款人", "早八人", "特种兵",
                "脆皮大学生", "清澈愚蠢", "发疯文学", "精神状态良好"
            ]
        }
    
    def _init_scenario_contexts(self) -> Dict[ScenarioType, Dict[str, Any]]:
        """初始化场景上下文"""
        return {
            ScenarioType.RECORD_SUCCESS: {
                "context": "用户成功记录一笔支出",
                "emotion": "positive",
                "formality": "low"
            },
            ScenarioType.BUDGET_WARNING: {
                "context": "预算使用接近阈值",
                "emotion": "neutral",
                "formality": "medium"
            },
            ScenarioType.BUDGET_EXCEEDED: {
                "context": "预算超支",
                "emotion": "empathetic",
                "formality": "low"
            },
            ScenarioType.DAILY_REPORT: {
                "context": "每日消费总结",
                "emotion": "neutral",
                "formality": "low"
            },
            ScenarioType.WEEKLY_REPORT: {
                "context": "每周消费总结",
                "emotion": "positive",
                "formality": "low"
            },
            ScenarioType.SAVING_ACHIEVEMENT: {
                "context": "达成省钱目标",
                "emotion": "excited",
                "formality": "low"
            },
            ScenarioType.EXPENSIVE_REMINDER: {
                "context": "大额消费提醒",
                "emotion": "caring",
                "formality": "medium"
            },
            ScenarioType.CLARIFICATION: {
                "context": "需要用户澄清信息",
                "emotion": "neutral",
                "formality": "low"
            },
            ScenarioType.GREETING: {
                "context": "开场问候",
                "emotion": "friendly",
                "formality": "low"
            },
            ScenarioType.ERROR: {
                "context": "系统错误",
                "emotion": "apologetic",
                "formality": "low"
            }
        }
    
    def generate_response(
        self,
        scenario: ScenarioType,
        data: Dict[str, Any],
        style: Optional[ExpressionStyle] = None,
        user_preference: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        生成同龄人化响应
        
        Args:
            scenario: 场景类型
            data: 数据参数（金额、分类、百分比等）
            style: 指定风格（不指定则随机选择）
            user_preference: 用户偏好设置
            
        Returns:
            生成的响应文本
        """
        if scenario not in self.templates:
            return "好的，已记录。"
        
        templates = self.templates[scenario]
        
        # 根据用户偏好或随机选择风格
        if style:
            templates = [t for t in templates if t.style == style]
        elif user_preference and user_preference.get("preferred_style"):
            preferred = ExpressionStyle(user_preference["preferred_style"])
            templates = [t for t in templates if t.style == preferred]
        
        if not templates:
            templates = self.templates[scenario]
        
        # 随机选择一个模板组
        template_group = random.choice(templates)
        
        # 随机选择具体模板
        template = random.choice(template_group.templates)
        
        # 填充数据
        try:
            response = template.format(**data)
        except KeyError:
            # 如果数据不匹配，使用默认模板
            response = self._get_default_response(scenario, data)
        
        # 随机添加emoji
        if random.random() < 0.7:  # 70%概率添加emoji
            emoji = random.choice(template_group.emoji_pool)
            if emoji not in response:
                response += f" {emoji}"
        
        return response
    
    def _get_default_response(self, scenario: ScenarioType, data: Dict[str, Any]) -> str:
        """获取默认响应"""
        defaults = {
            ScenarioType.RECORD_SUCCESS: f"已记录{data.get('category', '支出')} {data.get('amount', '')}元",
            ScenarioType.BUDGET_WARNING: f"{data.get('category', '该项')}预算已使用{data.get('percentage', '')}%",
            ScenarioType.BUDGET_EXCEEDED: f"{data.get('category', '该项')}预算超支{data.get('exceeded', '')}元",
            ScenarioType.DAILY_REPORT: f"今日消费{data.get('total', '')}元",
            ScenarioType.WEEKLY_REPORT: f"本周消费{data.get('total', '')}元",
            ScenarioType.SAVING_ACHIEVEMENT: f"恭喜节省{data.get('amount', '')}元",
            ScenarioType.EXPENSIVE_REMINDER: f"大额支出提醒：{data.get('amount', '')}元",
            ScenarioType.CLARIFICATION: "能再详细说明一下吗？",
            ScenarioType.GREETING: "你好！开始记账吧",
            ScenarioType.ERROR: "抱歉，出了点问题"
        }
        return defaults.get(scenario, "已处理")
    
    def get_system_prompt(self, context: Optional[str] = None) -> str:
        """
        获取AI系统提示词
        
        Args:
            context: 额外上下文
            
        Returns:
            系统提示词
        """
        base_prompt = """你是一个贴心的校园财务助手，专门帮助大学生管理日常支出。

【人设特点】
- 你是同龄人的朋友，用Z世代的语言风格交流
- 你懂大学生的梗，会用"get"、"yyds"、"绝绝子"等网络用语
- 你温柔但不矫情，幽默但不油腻
- 你理解学生的经济压力，从不制造焦虑

【语言风格】
- 使用轻松随意的口语，像朋友聊天
- 适当使用emoji增加亲和力
- 避免说教和命令式语气
- 多用鼓励和共情，少用警告和批评

【交流原则】
- 记账成功时：热情肯定，让用户有成就感
- 预算预警时：温柔提醒，强调"还有空间"
- 超支时：安慰理解，不指责
- 询问时：自然随意，不让用户尴尬
- 出错时：诚恳道歉，不甩锅

【常用表达】
- 肯定："okk"、"好嘞"、"收到"、"搞定"
- 鼓励："继续保持"、"相信你能行"、"拿捏住了"
- 安慰："没关系"、"抱抱你"、"下次注意就好"
- 询问："emm"、"没太get到"、"能再说一下吗"

【禁忌】
- 不说教、不批评
- 不用"您"，用"你"
- 不制造焦虑和压力
- 不过度热情让人尴尬"""
        
        if context:
            base_prompt += f"\n\n【当前场景】\n{context}"
        
        return base_prompt
    
    def enhance_ai_prompt(self, user_message: str, scenario: Optional[ScenarioType] = None) -> str:
        """
        增强AI提示词，融入同龄人化风格
        
        Args:
            user_message: 用户消息
            scenario: 场景类型
            
        Returns:
            增强后的提示词
        """
        system_prompt = self.get_system_prompt()
        
        if scenario and scenario in self.scenario_contexts:
            context = self.scenario_contexts[scenario]
            scenario_hint = f"\n当前场景：{context['context']}，情绪基调：{context['emotion']}"
            system_prompt += scenario_hint
        
        return system_prompt
    
    def get_conversation_style_guide(self) -> Dict[str, Any]:
        """获取对话风格指南"""
        return {
            "tone": "friendly_casual",
            "formality_level": "low",
            "emoji_usage": "frequent",
            "sentence_length": "short",
            "vocabulary_type": "internet_slang",
            "avoid": [
                "说教语气",
                "过度正式",
                "制造焦虑",
                "命令式表达",
                "过度热情"
            ],
            "embrace": [
                "共情理解",
                "幽默化解",
                "积极鼓励",
                "自然随意",
                "真诚道歉"
            ]
        }


# 全局服务实例
peer_expression_service = PeerExpressionService()
