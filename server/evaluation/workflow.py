"""
LangGraph workflow for the evaluation pipeline.

This module defines a stateful workflow for resume evaluation using LangGraph.
The workflow orchestrates resume parsing and fitment scoring as separate nodes.
"""

from typing import TypedDict, Optional
from sqlalchemy.orm import Session
from langgraph.graph import StateGraph, END

from ..resume_parser.service import ResumeParserService
from ..resume_parser.schema import ParsedResumeResponse
from ..fitment_score.service import FitmentScoreService
from ..fitment_score.schema import FitmentScoreResponse


class EvaluationState(TypedDict):
    """State for the evaluation workflow."""
    # Input
    application_id: str
    candidate_id: str
    job_id: str
    resume_url: str
    job_description: str
    required_skills: Optional[list[str]]
    required_experience_years: Optional[float]
    db: Optional[Session]
    
    # Intermediate state
    resume_id: Optional[str]
    parsed_resume: Optional[ParsedResumeResponse]
    
    # Output
    fitment_result: Optional[FitmentScoreResponse]
    error: Optional[str]


class EvaluationWorkflow:
    """LangGraph workflow for resume evaluation."""
    
    def __init__(self):
        self.resume_parser_service = ResumeParserService()
        self.fitment_score_service = FitmentScoreService()
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(EvaluationState)
        
        # Add nodes
        workflow.add_node("parse_resume", self._parse_resume_node)
        workflow.add_node("calculate_fitment", self._calculate_fitment_node)
        
        # Set entry point
        workflow.set_entry_point("parse_resume")
        
        # Add linear edges
        workflow.add_edge("parse_resume", "calculate_fitment")
        workflow.add_edge("calculate_fitment", END)
        
        return workflow.compile()
    
    async def _parse_resume_node(self, state: EvaluationState) -> dict:
        """Node for parsing resume."""
        try:
            resume_id = f"resume_{state['candidate_id']}_{state['application_id']}"
            parsed_resume = await self.resume_parser_service.parse_resume(
                resume_id=resume_id,
                candidate_id=state['candidate_id'],
                file_url=state['resume_url'],
                file_type="pdf",
                db=state.get('db')
            )
            
            return {
                "resume_id": resume_id,
                "parsed_resume": parsed_resume,
                "error": None
            }
        except Exception as e:
            return {
                "error": f"Resume parsing failed: {str(e)}"
            }
    
    async def _calculate_fitment_node(self, state: EvaluationState) -> dict:
        """Node for calculating fitment score."""
        if state.get("error"):
            return state
        
        try:
            fitment_result = await self.fitment_score_service.calculate_fitment_from_parsed_resume(
                parsed_resume=state["parsed_resume"],
                job_description=state["job_description"],
                job_id=state["job_id"],
                candidate_id=state["candidate_id"],
                resume_id=state["resume_id"],
                required_skills=state.get("required_skills") or [],
                required_experience_years=state.get("required_experience_years") or 0,
                db=state.get("db")
            )
            
            return {
                "fitment_result": fitment_result
            }
        except Exception as e:
            return {
                "error": f"Fitment scoring failed: {str(e)}"
            }
    
    async def run(self, initial_state: EvaluationState) -> EvaluationState:
        """Run the evaluation workflow."""
        config = {"configurable": {"thread_id": initial_state["application_id"]}}
        result = await self.graph.ainvoke(initial_state, config=config)
        return result
