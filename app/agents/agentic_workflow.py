from __future__ import annotations

import logging
from typing import Any, Union, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph
from langchain.agents import create_agent

from app.agents.schema import AgentReportState, ReportInputState, ReportOutputState, ReportOutline, ReviewResult, ResearchReflection
from app.agents.tools import get_book_structure, search_book_content, search_web_info
from app.core.config import Settings
from app.llm.chat_model import get_chat_model
from app.services.book_meta_service import get_book_meta

logger = logging.getLogger(__name__)

# 1. Book Expert: 专注于书内细节、结构和核心内容
BOOK_EXPERT_SYSTEM_PROMPT = """你是一位专业的书籍内容专家。
你的任务是深入研究书籍的内部结构和具体内容。
你需要关注：
1. 书籍的完整目录结构。
2. 核心章节的关键论点和细节。
3. 作者在书中的写作风格和叙事技巧。
4. 书中的金句、案例或关键数据。

你可以调用工具来查看目录或搜索书内片段。
收集完成后，请系统地总结你的发现，并以“内部研究完成”作为最后一段话的开头。"""

# 2. Context Researcher: 专注于作者背景、社会影响和同类对比
CONTEXT_RESEARCHER_SYSTEM_PROMPT = """你是一位专业的书籍背景研究员。
你的任务是挖掘书籍之外的相关信息。
你需要关注：
1. 作者的生平背景、创作动机及其他代表作。
2. 书籍出版时的社会历史背景及其产生的影响。
3. 媒体、专家或大众对本书的主流评价（褒贬均可）。
4. 本书与同类经典作品的对比及其独特价值。

你可以调用联网搜索工具获取信息。
收集完成后，请系统地总结你的发现，并以“外部研究完成”作为最后一段话的开头。"""

# 3. Research Reflector: 负责审视研究素材是否充分
RESEARCH_REFLECTOR_SYSTEM_PROMPT = """你是一位资深的研究主管。
你的任务是审视当前“书籍专家”和“背景研究员”搜集的素材是否足以支撑一份高质量、有深度的读书报告。

你需要检查：
1. 素材是否覆盖了用户的所有特殊要求？
2. 是否既有深入的书内细节，又有广阔的外部视角？
3. 是否存在明显的逻辑断层或信息缺失？

if素材充足，请输出 sufficient=True，next_action="none"。
        如果不足，请指出缺失的具体方向，并根据缺失内容的类型指定下一步行动：
        - 缺失书内细节、结构、原文精华 -> next_action="book_expert"
        - 缺失作者背景、社会影响、同类对比 -> next_action="context_researcher"
        - 两者都缺失 -> next_action="both" """

def build_agentic_report_graph(settings: Settings):
    model = get_chat_model(settings)
    
    # 1. 定义研究员 Agents
    book_expert_agent = create_agent(
        model=model,
        tools=[get_book_structure, search_book_content],
        system_prompt=BOOK_EXPERT_SYSTEM_PROMPT
    )
    
    context_researcher_agent = create_agent(
        model=model,
        tools=[search_web_info],
        system_prompt=CONTEXT_RESEARCHER_SYSTEM_PROMPT
    )

    # 封装 Node 以处理并行同步计数
    def node_book_expert(state: AgentReportState, config: RunnableConfig) -> dict[str, Any]:
        on_progress = config.get("configurable", {}).get("on_progress")
        if on_progress:
            on_progress("书籍专家正在深入研读内容...", 1)
        result = book_expert_agent.invoke(state, config)
        updates = result if isinstance(result, dict) else {"messages": [result]}
        updates["book_expert_done"] = True 
        return updates

    def node_context_researcher(state: AgentReportState, config: RunnableConfig) -> dict[str, Any]:
        on_progress = config.get("configurable", {}).get("on_progress")
        if on_progress:
            on_progress("背景研究员正在搜集外部信息...", 1)
        result = context_researcher_agent.invoke(state, config)
        updates = result if isinstance(result, dict) else {"messages": [result]}
        updates["context_researcher_done"] = True
        return updates

    # 2. 研究反思节点（并行同步栅栏）
    def node_research_reflector(state: AgentReportState, config: RunnableConfig) -> dict[str, Any]:
        on_progress = config.get("configurable", {}).get("on_progress")
        if on_progress:
            on_progress("研究主管正在评估素材充分性...", 2)
            
        # 分别检查两个研究员的完成情况
        next_action = state.get("next_research_action", "none")
        
        if next_action in ["both", "none"]:
            # 第一轮或明确要求两者时，需等待双方都完成
            if not (state.get("book_expert_done") and state.get("context_researcher_done")):
                return {"status": "waiting"} 
        elif next_action == "book_expert":
            if not state.get("book_expert_done"):
                return {"status": "waiting"}
        elif next_action == "context_researcher":
            if not state.get("context_researcher_done"):
                return {"status": "waiting"}

        # 汇总研究成果
        research_context = ""
        for msg in reversed(state["messages"]):
            if msg.type == "ai" and not msg.tool_calls:
                content = str(msg.content)
                if "内部研究完成" in content or "外部研究完成" in content:
                    research_context += f"\n{content}"
        
        reflector_prompt = f"""[当前研究素材]
        {research_context}
        
        [用户要求]
        {state['user_requirements']}
        
        请评估素材是否充分。"""
        
        structured_llm = model.with_structured_output(ResearchReflection, method="json_mode")
        try:
            reflection: ResearchReflection = structured_llm.invoke([
                SystemMessage(content=RESEARCH_REFLECTOR_SYSTEM_PROMPT + "\n请严格输出 JSON 格式，包含字段：sufficient (bool), missing_info (str or null), next_action (str)。"),
                HumanMessage(content=reflector_prompt)
            ])
            
            return {
                "research_feedback": reflection.missing_info if not reflection.sufficient else None,
                "research_notes": research_context,
                "next_research_action": reflection.next_action if not reflection.sufficient else "none",
                "status": "research_sufficient" if reflection.sufficient else "research_insufficient",
                "research_retry_count": state.get("research_retry_count", 0) + (0 if reflection.sufficient else 1),
                # 重置完成标记，为下一轮潜在的重试做准备
                "book_expert_done": False,
                "context_researcher_done": False
            }
        except Exception as e:
            logger.error(f"Research reflector failed: {e}")
            return {"status": "failed", "error": f"研究反思失败: {e}"}

    # 3. 规划节点：生成结构化大纲
    def node_planner(state: AgentReportState, config: RunnableConfig) -> dict[str, Any]:
        on_progress = config.get("configurable", {}).get("on_progress")
        if on_progress:
            on_progress("写作专家正在规划报告大纲...", 3)
        research_context = state.get("research_notes", "")
        if not research_context:
            # 回退方案：从消息流中提取
            for msg in reversed(state["messages"]):
                if msg.type == "ai" and not msg.tool_calls:
                    research_context = str(msg.content)
                    break
        
        if not research_context:
            return {"status": "failed", "error": "未能产出有效的背景信息"}

        planner_prompt = f"""根据以下研究成果和用户要求，规划一份读书报告的大纲。
        
        大纲应尽量包含以下核心板块：
        1. 书籍基本信息（书名、作者、作者背景简述）
        2. 书籍内容梗概
        3. 重点分析评价（主题思想、结构与叙事手法、人物与语言、关键内容分析、同类作品比较）
        4. 个人反思与联系（需融合用户理解）
        5. 总结与推荐
        
        [用户要求]
        {state['user_requirements']}
        
        [用户读后感/理解]
        {state['user_feelings']}
        
        [研究背景]
        {research_context}
        
        请输出一份结构清晰、逻辑严密的大纲。"""
        
        structured_llm = model.with_structured_output(ReportOutline, method="json_mode")
        try:
            outline: ReportOutline = structured_llm.invoke([
                SystemMessage(content="你是一位擅长结构化表达的写作专家。请严格输出 JSON 格式，包含字段：title (str), sections (list of objects with heading and bullets)。"),
                HumanMessage(content=planner_prompt)
            ])
            
            md_lines = [f"# {outline.title}"]
            for sec in outline.sections:
                md_lines.append(f"\n## {sec.heading}")
                for b in sec.bullets:
                    md_lines.append(f"- {b}")
            
            return {
                "outline_json": outline.dict(),
                "outline_markdown": "\n".join(md_lines),
                "research_notes": research_context,
                "status": "outlined"
            }
        except Exception as e:
            logger.error(f"Planner node failed: {e}")
            return {"status": "failed", "error": f"规划大纲失败: {e}"}

    # 3. 执行节点：扩写正文
    def node_writer(state: AgentReportState, config: RunnableConfig) -> dict[str, Any]:
        on_progress = config.get("configurable", {}).get("on_progress")
        if on_progress:
            on_progress("读书博主正在撰写报告正文...", 4)
        if not state.get("outline_markdown"):
            return {"status": "failed", "error": "缺失大纲，无法扩写"}
            
        feedback_context = ""
        if state.get("review_feedback"):
            feedback_context = f"\n\n[上轮审核反馈]\n{state['review_feedback']}\n请根据以上反馈对报告进行针对性修改。"
            
        writer_prompt = f"""请根据以下大纲和研究成果，撰写一份完整的读书报告。{feedback_context}
        
        [大纲]
        {state['outline_markdown']}
        
        [研究成果背景]
        {state.get('research_notes', '')}
        
        要求：
        1. 保持 Markdown 格式。
        2. 语言生动、专业，且贴合原文。
        3. 融合用户的理解与要求。
        4. 不要杜撰书中未提及的事实。"""
        
        try:
            res = model.invoke([
                SystemMessage(content="你是一位文字功底深厚的读书博主。"),
                HumanMessage(content=writer_prompt)
            ])
            return {
                "report_markdown": res.content,
                "status": "completed"
            }
        except Exception as e:
            logger.error(f"Writer node failed: {e}")
            return {"status": "failed", "error": f"扩写报告失败: {e}"}

    # 4. 审核节点：检查报告质量
    def node_reviewer(state: AgentReportState, config: RunnableConfig) -> dict[str, Any]:
        on_progress = config.get("configurable", {}).get("on_progress")
        if on_progress:
            on_progress("资深编辑正在审核报告质量...", 5)
        report = state.get("report_markdown")
        if not report:
            return {"status": "failed", "error": "缺失报告，无法审核"}
            
        reviewer_prompt = f"""你是一位严苛的读书报告编辑。
        请根据以下要求审核这份读书报告：
        1. 是否完整覆盖了大纲中的所有要点？
        2. 语言是否生动、专业？
        3. 是否融合了用户的感想和特殊要求？
        4. 是否存在杜撰或逻辑不通的地方？
        
        [用户要求]
        {state['user_requirements']}
        
        [大纲]
        {state['outline_markdown']}
        
        [读书报告正文]
        {report}
        
        如果通过审核，请输出 approved=True。如果不通过，请输出 approved=False 并给出具体的修改建议。"""
        
        structured_llm = model.with_structured_output(ReviewResult, method="json_mode")
        try:
            review: ReviewResult = structured_llm.invoke([
                SystemMessage(content="你是一位专业的资深编辑。请严格输出 JSON 格式，包含字段：approved (bool), feedback (str or null)。"),
                HumanMessage(content=reviewer_prompt)
            ])
            
            return {
                "review_feedback": review.feedback if not review.approved else None,
                "status": "reviewed" if review.approved else "revision_needed",
                "revision_count": state.get("revision_count", 0) + (0 if review.approved else 1)
            }
        except Exception as e:
            logger.error(f"Reviewer node failed: {e}")
            return {"status": "failed", "error": f"审核报告失败: {e}"}

    # 5. 润色节点：美化排版与语气调整
    def node_polisher(state: AgentReportState, config: RunnableConfig) -> dict[str, Any]:
        on_progress = config.get("configurable", {}).get("on_progress")
        if on_progress:
            on_progress("排版专家正在进行最后的润色...", 6)
        report = state.get("report_markdown")
        if not report:
            return {"status": "failed", "error": "缺失报告，无法润色"}
            
        style = state.get("report_style", "读书博主风")
        polisher_prompt = f"""你是一位专业的排版美化专家和润色编辑。
        请将以下读书报告调整为“{style}”风格。
        
        要求：
        1. 优化段落结构，使其更易于阅读。
        2. 根据风格调整语气（例如：博主风可以多用 Emoji 和感叹号；严肃风则保持克制专业）。
        3. 增加关键金句的加粗显示。
        4. 保持 Markdown 格式。
        5. 直接输出 Markdown 正文内容，不要将输出包裹在 ```markdown 或 ``` 代码块中。
        
        [原始报告]
        {report}"""
        
        try:
            res = model.invoke([
                SystemMessage(content="你是一位擅长排版和风格化润色的专家。"),
                HumanMessage(content=polisher_prompt)
            ])
            return {
                "report_markdown": res.content,
                "status": "completed"
            }
        except Exception as e:
            logger.error(f"Polisher node failed: {e}")
            return {"status": "failed", "error": f"润色报告失败: {e}"}

    # 构建图
    # 明确指定内部 State, 输入 Input 和 输出 Output 的 schema
    workflow = StateGraph(
        state_schema=AgentReportState,
        input_schema=ReportInputState,
        output_schema=ReportOutputState
    )
    
    workflow.add_node("book_expert", node_book_expert)
    workflow.add_node("context_researcher", node_context_researcher)
    workflow.add_node("research_reflector", node_research_reflector)
    workflow.add_node("planner", node_planner)
    workflow.add_node("writer", node_writer)
    workflow.add_node("reviewer", node_reviewer)
    workflow.add_node("polisher", node_polisher)
    
    # 1. 设置起始入口：恢复并行分流 (Fan-out)
    workflow.add_node("research_entry", lambda x: x)
    workflow.set_entry_point("research_entry")
    
    # 2. 连接并行研究分支
    workflow.add_edge("research_entry", "book_expert")
    workflow.add_edge("research_entry", "context_researcher")
    
    # 3. 两个分支最终汇合 (Fan-in) 到研究反思节点（由同步栅栏控制执行）
    workflow.add_edge("book_expert", "research_reflector")
    workflow.add_edge("context_researcher", "research_reflector")
    
    def route_after_research_reflector(state: AgentReportState) -> str:
         status = state.get("status")
         if status == "failed":
             return END
         if status == "waiting":
             # 同步栅栏：如果还有研究员没跑完，结束当前分支的执行，等待另一个分支触发
             return END
         if status == "research_sufficient":
             return "planner"
         if state.get("research_retry_count", 0) >= 2:
             logger.warning("Reached max research retry count, proceeding to planner.")
             return "planner"
         
         next_action = state.get("next_research_action", "book_expert")
         if next_action == "both":
             return "research_entry" 
         if next_action in ["book_expert", "context_researcher"]:
             return next_action
         return "planner" 

    workflow.add_conditional_edges("research_reflector", route_after_research_reflector)
    
    def route_after_planner(state: AgentReportState) -> str:
        if state.get("status") == "failed":
            return END
        if state.get("workflow_mode") == "outline":
            return END
        return "writer"

    def route_after_reviewer(state: AgentReportState) -> str:
        if state.get("status") == "failed":
            return END
        if state.get("status") == "reviewed":
            return "polisher"
        if state.get("revision_count", 0) >= 3:
            logger.warning("Reached max revision count, proceeding to polisher.")
            return "polisher"
        return "writer"

    workflow.add_conditional_edges("planner", route_after_planner)
    workflow.add_edge("writer", "reviewer")
    workflow.add_conditional_edges("reviewer", route_after_reviewer)
    workflow.add_edge("polisher", END)
    
    return workflow.compile()

def run_agent_report_workflow(
    settings: Settings,
    book_id: str,
    user_requirements: str | None = None,
    user_feelings: str | None = None,
    style: str = "读书博主风",
    mode: str = "report",
    on_progress: Any = None
) -> dict[str, Any]:
    """运行书籍研究与报告生成工作流"""
    app = build_agentic_report_graph(settings)
    
    # 获取书籍元数据，增强初始 Prompt
    meta = get_book_meta(settings, book_id)
    book_info = f"书籍 (ID: {book_id}"
    if meta.title:
        book_info += f", 书名: {meta.title}"
    if meta.author:
        book_info += f", 作者: {meta.author}"
    book_info += ")"
    
    initial_query = f"请针对{book_info}展开研究。"
    if user_requirements:
        initial_query += f"\n用户特别要求：{user_requirements}"
    if user_feelings:
        initial_query += f"\n用户的初步感想：{user_feelings}"
        
    # 构造符合 ReportInputState 且包含消息流的初始数据
    # 虽然输入 schema 定义为 ReportInputState，但 LangGraph 会自动合并到内部 State
    inputs = {
        "messages": [HumanMessage(content=initial_query)],
        "book_id": book_id,
        "user_requirements": user_requirements or "",
        "user_feelings": user_feelings or "",
        "report_style": style,
        "workflow_mode": mode,
        "revision_count": 0,
        "review_feedback": None,
        "research_retry_count": 0,
        "book_expert_done": False,
        "context_researcher_done": False,
        "research_feedback": None,
        "next_research_action": "none",
        "research_notes": ""
    }
    
    # 设置 recursion_limit 防止无限循环，默认 25 太小，对于复杂 Agent 建议 50-100
    config = {
        "configurable": {
            "settings": settings,
            "on_progress": on_progress
        }
        # "recursion_limit": 50
    }
    
    try:
        return app.invoke(inputs, config=config)
    except Exception as e:
        logger.exception(f"LangGraph workflow invocation failed for book {book_id}")
        return {"status": "failed", "error": f"工作流执行异常: {e}"}
