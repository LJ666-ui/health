"""
ZhiHealth Ollama大模型调用模块
- 本地Ollama API对接（支持千问qwen2系列）
- 流式/非流式响应
- Prompt模板集成
- 超时控制与重试
- 结果缓存（相同查询5分钟缓存）
"""

import json
import hashlib
import time
import threading
from typing import Dict, List, Optional, Any, Generator, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import requests
from loguru import logger


# ==================== 配置 ====================

@dataclass
class OllamaConfig:
    """Ollama配置"""
    host: str = "http://localhost:11434"
    default_model: str = "qwen2:7b"
    timeout: int = 120           # 单次请求超时（秒），AI分析可能较慢
    max_retries: int = 2         # 最大重试次数
    retry_delay: float = 2.0     # 重试间隔（秒）
    stream_chunk_size: int = 512 # 流式响应块大小
    cache_ttl: int = 300         # 缓存有效期（秒）= 5分钟
    max_context_length: int = 8192  # 最大上下文长度（token估算）


# 全局配置实例
config = OllamaConfig()


# ==================== 响应数据结构 ====================

@dataclass
class ChatMessage:
    """聊天消息"""
    role: str          # system/user/assistant
    content: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {"role": self.role, "content": self.content}


@dataclass
class OllamaResponse:
    """Ollama响应结果"""
    success: bool
    content: str = ""
    model: str = ""
    total_duration_ms: int = 0
    prompt_eval_count: int = 0
    eval_count: int = 0
    error: str = ""
    is_cached: bool = False
    response_time_ms: int = 0


# ==================== 缓存 ====================

_response_cache: Dict[str, Dict] = {}
_cache_lock = threading.Lock()


def _cache_key(model: str, messages: List[Dict]) -> str:
    """生成缓存key"""
    raw = json.dumps({"model": model, "messages": messages}, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()


def _get_from_cache(key: str) -> Optional[Dict]:
    """从缓存获取"""
    with _cache_lock:
        if key in _response_cache:
            entry = _response_cache[key]
            if time.time() - entry["timestamp"] < config.cache_ttl:
                return entry["data"]
            else:
                del _response_cache[key]
    return None


def _set_cache(key: str, data: Dict):
    """写入缓存"""
    with _cache_lock:
        _response_cache[key] = {
            "data": data,
            "timestamp": time.time()
        }


# ==================== 核心调用类 ====================

class OllamaClient:
    """Ollama大模型客户端"""

    def __init__(self, cfg: OllamaConfig = None):
        self.config = cfg or config
        self.session = requests.Session()
        self._check_connection()

    def _check_connection(self) -> bool:
        """检查Ollama连接状态"""
        try:
            resp = self.session.get(f"{self.config.host}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                logger.info(f"[Ollama] 连接成功，可用模型: {model_names}")
                return True
        except Exception as e:
            logger.warning(f"[Ollama] 连接检查失败: {e}")
        return False

    @property
    def is_online(self) -> bool:
        """检查是否在线"""
        try:
            resp = self.session.get(f"{self.config.host}/api/tags", timeout=3)
            return resp.status_code == 200
        except:
            return False

    def list_models(self) -> List[Dict]:
        """列出所有可用模型"""
        try:
            resp = self.session.get(f"{self.config.host}/api/tags", timeout=10)
            if resp.status_code == 200:
                return resp.json().get("models", [])
        except Exception as e:
            logger.error(f"[Ollama] 获取模型列表失败: {e}")
        return []

    def chat(
        self,
        messages: List[Dict],
        model: str = None,
        stream: bool = False,
        temperature: float = 0.7,
        top_p: float = 0.9,
        use_cache: bool = True
    ) -> OllamaResponse:
        """
        非流式聊天（完整返回）

        Args:
            messages: 消息列表 [{"role": "system/user", "content": "..."}]
            model: 模型名称
            stream: 是否流式（此处为False）
            temperature: 温度参数
            top_p: top-p采样
            use_cache: 是否使用缓存

        Returns:
            OllamaResponse
        """
        model = model or self.config.default_model
        start_time = time.time()

        # 缓存检查
        if use_cache and len(messages) >= 1:
            key = _cache_key(model, messages)
            cached = _get_from_cache(key)
            if cached:
                logger.info(f"[Ollama] 命中缓存")
                return OllamaResponse(
                    success=True,
                    content=cached["content"],
                    model=model,
                    is_cached=True,
                    response_time_ms=int((time.time() - start_time) * 1000)
                )

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "num_predict": 4096,
            }
        }

        last_error = ""
        for attempt in range(self.config.max_retries + 1):
            try:
                logger.info(f"[Ollama] 请求模型={model}, 尝试={attempt+1}/{self.config.max_retries+1}")
                resp = self.session.post(
                    f"{self.config.host}/api/chat",
                    json=payload,
                    timeout=self.config.timeout,
                    headers={"Content-Type": "application/json"}
                )

                if resp.status_code == 200:
                    data = resp.json()
                    content = data.get("message", {}).get("content", "")

                    result = OllamaResponse(
                        success=True,
                        content=content,
                        model=model,
                        total_duration_ms=data.get("total_duration", 0) // 1_000_000,
                        prompt_eval_count=data.get("prompt_eval_count", 0),
                        eval_count=data.get("eval_count", 0),
                        response_time_ms=int((time.time() - start_time) * 1000)
                    )

                    # 写入缓存
                    if use_cache:
                        _set_cache(key, {"content": content})

                    logger.info(f"[Ollama] 响应成功, tokens={result.eval_count}, "
                                f"耗时={result.response_time_ms}ms")
                    return result

                else:
                    last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"

            except requests.exceptions.Timeout:
                last_error = f"请求超时 ({self.config.timeout}s)"
                logger.warning(f"[Ollama] {last_error}")
            except requests.exceptions.ConnectionError:
                last_error = "连接失败，请确认Ollama服务已启动"
                logger.error(f"[Ollama] {last_error}")
                break  # 连接失败不重试
            except Exception as e:
                last_error = str(e)[:200]
                logger.warning(f"[Ollama] 请求异常: {last_error}")

            if attempt < self.config.max_retries:
                time.sleep(self.config.retry_delay * (attempt + 1))

        logger.error(f"[Ollama] 最终失败: {last_error}")
        return OllamaResponse(
            success=False,
            error=f"模型调用失败: {last_error}",
            model=model,
            response_time_ms=int((time.time() - start_time) * 1000)
        )

    def chat_stream(
        self,
        messages: List[Dict],
        model: str = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        on_chunk: Callable[[str], None] = None
    ) -> Generator[str, None, OllamaResponse]:
        """
        流式聊天（逐块yield内容）

        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度
            top_p: top-p采样
            on_chunk: 每收到一块内容的回调

        Yields:
            文本片段(str)

        Returns (通过generator return):
            OllamaResponse
        """
        model = model or self.config.default_model
        start_time = time.time()
        full_content = ""

        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "num_predict": 4096,
            }
        }

        try:
            resp = self.session.post(
                f"{self.config.host}/api/chat",
                json=payload,
                timeout=self.config.timeout + 30,
                stream=True,
                headers={"Content-Type": "application/json"}
            )

            if resp.status_code != 200:
                error_msg = f"HTTP {resp.status_code}: {resp.text[:200]}"
                logger.error(f"[Ollama] 流式请求失败: {error_msg}")
                yield from ()
                return OllamaResponse(success=False, error=error_msg, model=model)

            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                try:
                    chunk_data = json.loads(line)
                    if chunk_data.get("done"):
                        break
                    delta = chunk_data.get("message", {}).get("content", "")
                    if delta:
                        full_content += delta
                        yield delta
                        if on_chunk:
                            on_chunk(delta)
                except json.JSONDecodeError:
                    continue

            final_resp = OllamaResponse(
                success=True,
                content=full_content,
                model=model,
                response_time_ms=int((time.time() - start_time) * 1000)
            )
            logger.info(f"[Ollama] 流式响应完成, 总长度={len(full_content)}, "
                        f"耗时={final_resp.response_time_ms}ms")
            return final_resp

        except requests.exceptions.Timeout:
            error = f"流式请求超时"
            logger.error(f"[Ollama] {error}")
            yield from ()
            return OllamaResponse(success=False, error=error, model=model)
        except Exception as e:
            error = str(e)[:200]
            logger.error(f"[Ollama] 流式异常: {error}")
            yield from ()
            return OllamaResponse(success=False, error=error, model=model)


# ============================================================
# 智能问答路由 - NLP → 数据库 / ML / 大模型
# ============================================================

class HealthChatBot:
    """
    智能健康问答机器人
    路由逻辑：
    1. NLP分析用户输入（分词→意图识别→实体提取）
    2. 根据意图路由到不同处理通道：
       - data_query → 从数据库查询实际数据
       - health_consult → 大模型通用健康咨询
       - risk_assessment → ML风险评估模型
       - report_generation → Prompt模板+大模型生成报告
       - suggestion_request → Prompt模板+大模型生成建议
       - chat_idle → 大模型闲聊
    """

    def __init__(self):
        from .nlp_processor import NLPProcessor
        from ..prompts.prompt_templates import prompt_manager

        self.nlp = NLPProcessor()
        self.ollama = OllamaClient()
        self.prompt_mgr = prompt_manager
        self.conversation_history: Dict[str, List[ChatMessage]] = {}

    def chat(
        self,
        user_id: str,
        message: str,
        context_data: Dict = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        处理用户消息并返回回复

        Args:
            user_id: 用户ID
            message: 用户消息
            context_data: 上下文数据（如用户的最新健康指标等）
            stream: 是否流式返回

        Returns:
            完整的回复字典
        """
        start_time = time.time()

        # 1. NLP分析
        nlp_result = self.nlp.analyze(message)
        intent_type = nlp_result["intent"]["type"]
        intent_confidence = nlp_result["intent"]["confidence"]
        slots = nlp_result["intent"]["slots"]

        logger.info(f"[ChatBot] user={user_id}, intent={intent_type}, "
                     f"confidence={intent_confidence:.2f}")

        # 2. 记录对话历史
        self._add_to_history(user_id, "user", message)

        # 3. 根据意图路由处理
        reply_content = ""
        analysis_result = None

        if intent_type == "data_query":
            reply_content, analysis_result = self._handle_data_query(slots, context_data)

        elif intent_type == "health_consult":
            reply_content, analysis_result = self._handle_health_consult(message, nlp_result, context_data)

        elif intent_type == "risk_assessment":
            reply_content, analysis_result = self._handle_risk_assessment(context_data)

        elif intent_type == "report_generation":
            reply_content, analysis_result = self._handle_report_generation(slots, context_data)

        elif intent_type == "suggestion_request":
            reply_content, analysis_result = self._handle_suggestion_request(slots, nlp_result, context_data)

        else:
            # chat_idle 或未知意图 → 直接走大模型
            reply_content = self._handle_general_chat(user_id, message, context_data)

        # 4. 记录助手回复到历史
        self._add_to_history(user_id, "assistant", reply_content)

        elapsed_ms = int((time.time() - start_time) * 1000)

        return {
            "reply": reply_content,
            "intent": intent_type,
            "confidence": intent_confidence,
            "nlp_detail": nlp_result,
            "analysis": analysis_result,
            "elapsed_ms": elapsed_ms,
            "model_used": self.ollama.config.default_model
        }

    def chat_stream(self, user_id: str, message: str, context_data: Dict = None):
        """流式聊天接口"""
        nlp_result = self.nlp.analyze(message)
        intent_type = nlp_result["intent"]["type"]
        self._add_to_history(user_id, "user", message)

        # 对于需要大模型的意图，走流式
        if intent_type in ("health_consult", "chat_idle", "suggestion_request"):
            rendered = self.prompt_mgr.render_chatbot(message, self._build_context_str(context_data))
            history_msgs = self._get_history_messages(user_id)
            messages = [
                {"role": "system", "content": rendered["system"]},
                *history_msgs,
                {"role": "user", "content": rendered["user"]}
            ]

            full_reply = ""
            for chunk in self.ollama.chat_stream(messages, on_chunk=None):
                full_reply += chunk
                yield {"type": "chunk", "content": chunk}

            self._add_to_history(user_id, "assistant", full_reply)
            yield {"type": "done", "reply": full_reply, "intent": intent_type}
        else:
            # 非流式意图先完整处理后一次性返回
            result = self.chat(user_id, message, context_data, stream=False)
            yield {"type": "done", **result}

    # ---- 各意图处理器 ----

    def _handle_data_query(self, slots: Dict, context_data: Dict) -> tuple:
        """处理数据查询意图"""
        metric = slots.get("metric", "")
        time_range = slots.get("time_range", "最近7天")

        # 构造查询提示
        prompt = (
            f"用户想查询{metric or '健康'}数据，时间范围：{time_range}。\n"
        )
        if context_data:
            prompt += f"\n当前可用数据:\n{json.dumps(context_data, ensure_ascii=False, indent=2)}\n\n"
            prompt += "请基于以上数据回答用户的数据查询问题。"

        messages = [{"role": "system", "content": "你是健康数据查询助手，直接给出数据事实。"},
                   {"role": "user", "content": prompt}]
        resp = self.ollama.chat(messages)

        return resp.content, {"query_metric": metric, "time_range": time_range}

    def _handle_health_consult(self, message: str, nlp_result: Dict, context_data: Dict) -> tuple:
        """处理健康咨询意图"""
        entities = nlp_result.get("entities", [])
        entity_summary = ", ".join([f"{e['text']}({e['type']})" for e in entities[:5]])

        context_str = self._build_context_str(context_data)
        rendered = self.prompt_mgr.render_chatbot(
            f"{message}\n\n[识别到的关键信息: {entity_summary}]",
            context_str
        )

        messages = [
            {"role": "system", "content": rendered["system"]},
            {"role": "user", "content": rendered["user"]}
        ]
        resp = self.ollama.chat(messages)

        return resp.content, {"entities": entities}

    def _handle_risk_assessment(self, context_data: Dict) -> tuple:
        """处理风险评估意图"""
        if context_data:
            variables = self._flatten_context_for_risk(context_data)
            try:
                rendered = self.prompt_mgr.render("risk_assessment", variables)
            except Exception:
                rendered = self.prompt_mgr.render_chatbot(
                    "请根据我的健康数据进行风险评估",
                    self._build_context_str(context_data)
                )
        else:
            rendered = self.prompt_mgr.render_chatbot(
                "请帮我进行健康风险评估",
                "暂无具体数据，请给出通用的风险评估框架和建议"
            )

        messages = [
            {"role": "system", "content": rendered["system"]},
            {"role": "user", "content": rendered["user"]}
        ]
        resp = self.ollama.chat(messages)

        return resp.content, {"assessment_type": "comprehensive"}

    def _handle_report_generation(self, slots: Dict, context_data: Dict) -> tuple:
        """处理报告生成意图"""
        report_type = slots.get("report_type", "综合报告")
        time_range = slots.get("time_range", "本周")

        context_str = self._build_context_str(context_data)
        prompt = f"请生成一份{report_type}，覆盖时间范围：{time_range}\n\n{context_str}"

        messages = [
            {"role": "system", "content": "你是专业的健康报告撰写专家。"},
            {"role": "user", "content": prompt}
        ]
        resp = self.ollama.chat(messages)

        return resp.content, {"report_type": report_type, "time_range": time_range}

    def _handle_suggestion_request(self, slots: Dict, nlp_result: Dict, context_data: Dict) -> tuple:
        """处理建议请求意图"""
        area = slots.get("improvement_area", "综合")

        context_str = self._build_context_str(context_data)
        rendered = self.prompt_mgr.render_chatbot(
            f"我想改善我的健康状况，重点关注：{area}",
            context_str
        )

        messages = [
            {"role": "system", "content": rendered["system"]},
            {"role": "user", "content": rendered["user"]}
        ]
        resp = self.ollama.chat(messages)

        return resp.content, {"focus_area": area}

    def _handle_general_chat(self, user_id: str, message: str, context_data: Dict) -> str:
        """处理通用聊天（闲聊/未识别意图）"""
        context_str = self._build_context_str(context_data)
        rendered = self.prompt_mgr.render_chatbot(message, context_str)

        history_msgs = self._get_history_messages(user_id)
        messages = [
            {"role": "system", "content": rendered["system"]},
            *history_msgs[-6:],   # 最近3轮对话作为上下文
            {"role": "user", "content": rendered["user"]}
        ]
        resp = self.ollama.chat(messages)
        return resp.content

    # ---- 工具方法 ----

    def _add_to_history(self, user_id: str, role: str, content: str):
        """添加消息到历史记录（最多保留20条）"""
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        self.conversation_history[user_id].append(ChatMessage(role=role, content=content))
        # 只保留最近20条
        if len(self.conversation_history[user_id]) > 20:
            self.conversation_history[user_id] = self.conversation_history[user_id][-20:]

    def _get_history_messages(self, user_id: str) -> List[Dict]:
        """获取格式化的历史消息（用于发给大模型）"""
        history = self.conversation_history.get(user_id, [])
        return [m.to_dict() for m in history]

    def _build_context_str(self, context_data: Dict) -> str:
        """将上下文数据转为文本"""
        if not context_data:
            return "（无额外上下文数据）"
        return json.dumps(context_data, ensure_ascii=False, indent=2)

    def _flatten_context_for_risk(self, context_data: Dict) -> Dict:
        """将上下文数据展平为风险Prompt变量"""
        flat = {}
        for k, v in context_data.items():
            if isinstance(v, dict):
                flat.update(v)
            else:
                flat[k] = v
        # 设置默认值防止模板渲染失败
        defaults = {
            "age": "35", "gender": "男", "bmi": "23.0",
            "resting_hr": "72", "hr_status": "正常",
            "avg_bp": "118/76", "bp_status": "正常",
            "fasting_glucose": "5.2", "glucose_status": "正常",
            "cholesterol": "4.8", "cholesterol_status": "正常",
            "steps": "6500", "activity_status": "偏低",
            "sleep_hours": "7.0", "sleep_status": "正常",
            "smoking_status": "否", "drinking_status": "偶尔",
            "family_history": "无特殊", "past_diseases": "无",
            "main_health_issues": "无明显不适", "health_goal": "保持健康"
        }
        for dk, dv in defaults.items():
            if dk not in flat or flat[dk] is None:
                flat[dk] = dv
        return flat


# ============================================================
# Flask API 接口
# ============================================================

def create_ollama_api(app=None):
    """创建Ollama/智能问答API路由"""
    from flask import request, jsonify

    bot = HealthChatBot()
    client = OllamaClient()

    @app.route('/api/ai/status', methods=['GET'])
    def ai_status():
        """AI服务状态检查"""
        return jsonify({
            "code": 200,
            "success": True,
            "data": {
                "ollama_online": client.is_online,
                "default_model": client.config.default_model,
                "available_models": [m["name"] for m in client.list_models()],
                "cache_enabled": True,
                "cache_ttl_seconds": client.config.cache_ttl
            }
        })

    @app.route('/api/ai/chat', methods=['POST'])
    def chat():
        """智能问答（非流式）"""
        data = request.get_json()
        message = data.get("message", "").strip()
        user_id = data.get("user_id", "anonymous")
        context_data = data.get("context")

        if not message:
            return jsonify({"code": 400, "success": False, "message": "消息不能为空"}), 400

        result = bot.chat(user_id, message, context_data)
        return jsonify({"code": 200, "success": True, "data": result})

    @app.route('/api/ai/chat/stream', methods=['POST'])
    def chat_stream():
        """智能问答（流式）- SSE格式"""
        from flask import Response

        data = request.get_json()
        message = data.get("message", "").strip()
        user_id = data.get("user_id", "anonymous")
        context_data = data.get("context")

        if not message:
            return jsonify({"code": 400, "success": False, "message": "消息不能为空"}), 400

        def generate():
            for chunk_result in bot.chat_stream(user_id, message, context_data):
                chunk_type = chunk_result.get("type", "")
                if chunk_type == "chunk":
                    yield f"data: {json.dumps(chunk_result, ensure_ascii=False)}\n\n"
                elif chunk_type == "done":
                    yield f"data: {json.dumps(chunk_result, ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"

        return Response(
            generate(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )

    @app.route('/api/ai/analyze/trend', methods=['POST'])
    def analyze_trend():
        """趋势分析（Prompt模板+大模型）"""
        data = request.get_json()
        from ..prompts.prompt_templates import prompt_manager

        variables = data.get("variables", {})
        try:
            rendered = prompt_manager.render("trend_analysis", variables)
        except KeyError as e:
            return jsonify({
                "code": 400, "success": False,
                "message": f"缺少必要变量: {e}"
            }), 400

        ollama = OllamaClient()
        resp = ollama.chat([
            {"role": "system", "content": rendered["system"]},
            {"role": "user", "content": rendered["user"]}
        ])

        return jsonify({
            "code": 200 if resp.success else 500,
            "success": resp.success,
            "data": {
                "analysis": resp.content if resp.success else None,
                "error": resp.error if not resp.success else None,
                "model": resp.model,
                "response_time_ms": resp.response_time_ms
            }
        })

    @app.route('/api/ai/analyze/risk', methods=['POST'])
    def analyze_risk():
        """风险评估（Prompt模板+大模型）"""
        data = request.get_json()
        from ..prompts.prompt_templates import prompt_manager

        variables = data.get("variables", {})
        try:
            rendered = prompt_manager.render("risk_assessment", variables)
        except KeyError as e:
            return jsonify({
                "code": 400, "success": False,
                "message": f"缺少必要变量: {e}"
            }), 400

        ollama = OllamaClient()
        resp = ollama.chat([
            {"role": "system", "content": rendered["system"]},
            {"role": "user", "content": rendered["user"]}
        ])

        return jsonify({
            "code": 200 if resp.success else 500,
            "success": resp.success,
            "data": {
                "assessment": resp.content if resp.success else None,
                "error": resp.error if not resp.success else None,
                "model": resp.model
            }
        })

    @app.route('/api/ai/models', methods=['GET'])
    def list_ai_models():
        """列出可用AI模型"""
        client = OllamaClient()
        models = client.list_models()
        return jsonify({
            "code": 200,
            "success": True,
            "data": {
                "models": models,
                "default": client.config.default_model,
                "online": client.is_online
            }
        })

    logger.info("[Ollama/AI] API路由注册完成")
    return app
