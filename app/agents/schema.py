from __future__ import annotations
import operator
from typing import Annotated, Any, Optional, Sequence, TypedDict
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class ReportSection(BaseModel):
    """读书报告的单个章节大纲。"""
    heading: str = Field(description="章节标题，例如：核心观点、作者背景等。")
    bullets: list[str] = Field(description="该章节下的关键点，每条建议不超过60字。")

class ReportOutline(BaseModel):
    """读书报告的完整大纲结构。"""
    title: str = Field(description="读书报告的总标题。")
    sections: list[ReportSection] = Field(description="报告包含的章节列表。")

class ReviewResult(BaseModel):
    """审核结果。"""
    approved: bool = Field(description="是否通过审核。")
    feedback: Optional[str] = Field(default=None, description="具体的修改建议，如果通过则可为空。")

class ResearchReflection(BaseModel):
    """研究反思结果。"""
    sufficient: bool = Field(description="当前搜集的素材是否足以支撑一份高质量报告。")
    missing_info: Optional[str] = Field(default=None, description="缺失的关键信息或需要进一步研究的方向。")
    next_action: str = Field(
        default="none", 
        description="下一步需要哪个研究员继续补充素材(book_expert, context_researcher, both, none)。"
    )

class ReportInputState(TypedDict):
    """读书报告工作流的输入状态。"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    book_id: str
    user_requirements: str
    user_feelings: str
    report_style: str  # 例如：读书博主风、严肃书评风、极简主义风
    workflow_mode: str  # report, outline, context

class ReportOutputState(TypedDict):
    """读书报告工作流的输出状态。"""
    outline_markdown: Optional[str]
    report_markdown: Optional[str]
    status: str
    error: Optional[str]

class AgentReportState(ReportInputState, ReportOutputState):
    """LangGraph 工作流的内部状态，继承自输入和输出状态。"""
    # 研究成果汇总（由 Researcher Agent 产出，供 Planner 使用）
    research_notes: str
    
    # 结构化中间产物
    outline_json: Optional[dict[str, Any]]

    # 审核反馈与重试计数
    review_feedback: Optional[str]
    revision_count: int

    # 研究反思反馈与重试计数
    research_feedback: Optional[str]
    research_retry_count: int
    
    # 研究同步标记
    book_expert_done: bool
    context_researcher_done: bool
    
    next_research_action: str
