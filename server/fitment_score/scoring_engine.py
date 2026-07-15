from typing import Dict, Any, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class DimensionScore:
    """Score for a single fitment dimension."""
    score: float
    reasoning: str
    weight: float


class ScoringEngine:
    """
    Isolated scoring engine for fitment calculation.
    Contains weighting logic and scoring algorithms.
    Unit-tested independently.
    """
    
    # Scoring weights (sum to 1.0)
    WEIGHTS = {
        "skills": 0.40,
        "experience": 0.30,
        "education": 0.15,
        "culture_fit": 0.15
    }
    
    def __init__(self):
        self.weights = self.WEIGHTS.copy()
    
    def calculate_overall_score(
        self,
        skills_score: float,
        experience_score: float,
        education_score: float,
        culture_fit_score: float
    ) -> float:
        """
        Calculate weighted overall fitment score.
        
        Args:
            skills_score: Skills match score (0.0-1.0)
            experience_score: Experience match score (0.0-1.0)
            education_score: Education match score (0.0-1.0)
            culture_fit_score: Culture fit score (0.0-1.0)
        
        Returns:
            Weighted overall score (0.0-1.0)
        """
        overall = (
            skills_score * self.weights["skills"] +
            experience_score * self.weights["experience"] +
            education_score * self.weights["education"] +
            culture_fit_score * self.weights["culture_fit"]
        )
        
        # Clamp to valid range
        return max(0.0, min(1.0, overall))
    
    def calculate_skills_score(
        self,
        candidate_skills: List[str],
        required_skills: List[str],
        bonus_skills: List[str] = None
    ) -> DimensionScore:
        """
        Calculate skills match score.
        
        Args:
            candidate_skills: List of candidate's skills
            required_skills: List of required skills
            bonus_skills: Optional list of bonus/relevant skills
        
        Returns:
            DimensionScore with score and reasoning
        """
        if not required_skills:
            return DimensionScore(
                score=1.0,
                reasoning="No required skills specified",
                weight=self.weights["skills"]
            )
        
        # Count matching skills
        required_set = set(skill.lower() for skill in required_skills)
        candidate_set = set(skill.lower() for skill in candidate_skills)
        
        matched = len(candidate_set & required_set)
        total_required = len(required_set)
        
        # Base score from required skills
        base_score = matched / total_required if total_required > 0 else 1.0
        
        # Bonus for extra relevant skills
        bonus_score = 0.0
        bonus_reasoning = ""
        if bonus_skills:
            bonus_set = set(skill.lower() for skill in bonus_skills)
            matched_bonus = len(candidate_set & bonus_set)
            bonus_score = min(0.1, matched_bonus * 0.02)  # Up to 10% bonus
            if matched_bonus > 0:
                bonus_reasoning = f" Has {matched_bonus} bonus skills."
        
        final_score = min(1.0, base_score + bonus_score)
        
        reasoning = (
            f"Candidate has {matched}/{total_required} required skills. "
            f"Base score: {base_score:.2f}.{bonus_reasoning}"
        )
        
        return DimensionScore(
            score=final_score,
            reasoning=reasoning,
            weight=self.weights["skills"]
        )
    
    def calculate_experience_score(
        self,
        candidate_years: float,
        required_years: float,
        relevant_experience: List[Dict[str, Any]] = None
    ) -> DimensionScore:
        """
        Calculate experience match score.
        
        Args:
            candidate_years: Candidate's total years of experience
            required_years: Required years of experience
            relevant_experience: Optional list of relevant experience entries
        
        Returns:
            DimensionScore with score and reasoning
        """
        if required_years == 0:
            return DimensionScore(
                score=1.0,
                reasoning="No experience requirement specified",
                weight=self.weights["experience"]
            )
        
        # Calculate ratio
        ratio = candidate_years / required_years if required_years > 0 else 1.0
        
        # Score based on ratio
        if ratio >= 1.5:
            score = 1.0
            reasoning = f"Exceeds requirement: {candidate_years:g} years vs {required_years:g} required"
        elif ratio >= 1.0:
            score = 0.9
            reasoning = f"Meets requirement: {candidate_years:g} years vs {required_years:g} required"
        elif ratio >= 0.8:
            score = 0.7
            reasoning = f"Slightly below requirement: {candidate_years:g} years vs {required_years:g} required"
        elif ratio >= 0.5:
            score = 0.5
            reasoning = f"Below requirement: {candidate_years:g} years vs {required_years:g} required"
        else:
            score = 0.2
            reasoning = f"Significantly below requirement: {candidate_years:g} years vs {required_years:g} required"
        
        # Bonus for relevant industry experience
        if relevant_experience and len(relevant_experience) > 0:
            score = min(1.0, score + 0.1)
            reasoning += f" Has {len(relevant_experience)} relevant experience entries."
        
        return DimensionScore(
            score=score,
            reasoning=reasoning,
            weight=self.weights["experience"]
        )
    
    def calculate_education_score(
        self,
        candidate_education: List[Dict[str, Any]],
        required_education: str = None,
        preferred_education: List[str] = None
    ) -> DimensionScore:
        """
        Calculate education match score.
        
        Args:
            candidate_education: List of candidate's education entries
            required_education: Required education level
            preferred_education: Optional list of preferred education fields
        
        Returns:
            DimensionScore with score and reasoning
        """
        if not required_education:
            return DimensionScore(
                score=1.0,
                reasoning="No education requirement specified",
                weight=self.weights["education"]
            )
        
        if not candidate_education:
            return DimensionScore(
                score=0.0,
                reasoning="No education information provided",
                weight=self.weights["education"]
            )
        
        # Check if required education is met
        required_lower = required_education.lower()
        score = 0.0
        reasoning = ""
        
        for edu in candidate_education:
            degree = edu.get("degree", "").lower()
            field = edu.get("field_of_study", "").lower()
            
            # Check degree match, including common degree abbreviations.
            bachelor_degree = degree in {'bs', 'b.s.', 'ba', 'b.a.', 'bsc', 'b.sc'}
            if required_lower in degree or degree in required_lower or (
                'bachelor' in required_lower and bachelor_degree
            ):
                score = 1.0
                reasoning = f"Meets requirement: {edu.get('degree')} in {edu.get('field_of_study')}"
                break
            
            # Check if higher degree
            higher_degrees = ["phd", "doctorate", "master", "m.s.", "m.sc"]
            if any(hd in degree for hd in higher_degrees) and "bachelor" in required_lower:
                score = 1.0
                reasoning = f"Exceeds requirement: {edu.get('degree')} vs required {required_education}"
                break
        
        # If no exact match, check for partial match
        if score == 0.0:
            for edu in candidate_education:
                if any(word in edu.get("degree", "").lower() for word in required_lower.split()):
                    score = 0.7
                    reasoning = f"Partial match: {edu.get('degree')}"
                    break
        
        # Bonus for preferred field of study
        if preferred_education and score > 0:
            for edu in candidate_education:
                field = edu.get("field_of_study", "").lower()
                if any(pref.lower() in field for pref in preferred_education):
                    score = min(1.0, score + 0.1)
                    reasoning += f" Preferred field match: {edu.get('field_of_study')}"
                    break
        
        if score == 0.0:
            reasoning = f"Does not meet requirement: {required_education}"
        
        return DimensionScore(
            score=score,
            reasoning=reasoning,
            weight=self.weights["education"]
        )
    
    def calculate_culture_fit_score(
        self,
        career_trajectory: List[Dict[str, Any]] = None,
        job_stability: float = None,
        growth_indicators: List[str] = None
    ) -> DimensionScore:
        """
        Calculate culture and growth fit score.
        
        Args:
            career_trajectory: Optional career progression data
            job_stability: Optional job stability score (0.0-1.0)
            growth_indicators: Optional list of growth indicators
        
        Returns:
            DimensionScore with score and reasoning
        """
        score = 0.5  # Default neutral score
        reasoning_parts = []
        
        # Analyze career trajectory
        if career_trajectory and len(career_trajectory) > 1:
            # Check for progression (increasing seniority)
            progression_count = 0
            for i in range(1, len(career_trajectory)):
                prev_role = career_trajectory[i-1].get("job_title", "").lower()
                curr_role = career_trajectory[i].get("job_title", "").lower()
                
                senior_keywords = ["senior", "lead", "manager", "director", "head", "principal"]
                if any(kw in curr_role for kw in senior_keywords) and not any(kw in prev_role for kw in senior_keywords):
                    progression_count += 1
            
            if progression_count > 0:
                score += 0.2
                reasoning_parts.append(f"Shows career progression ({progression_count} promotions)")
        
        # Job stability
        if job_stability is not None:
            if job_stability >= 0.8:
                score += 0.15
                reasoning_parts.append("High job stability")
            elif job_stability >= 0.5:
                score += 0.05
                reasoning_parts.append("Moderate job stability")
            else:
                score -= 0.1
                reasoning_parts.append("Low job stability")
        
        # Growth indicators
        if growth_indicators:
            score += min(0.15, len(growth_indicators) * 0.05)
            reasoning_parts.append(f"Shows {len(growth_indicators)} growth indicators")
        
        # Clamp score
        score = max(0.0, min(1.0, score))
        
        reasoning = ". ".join(reasoning_parts) if reasoning_parts else "Limited culture fit data available"
        
        return DimensionScore(
            score=score,
            reasoning=reasoning,
            weight=self.weights["culture_fit"]
        )
    
    def update_weights(self, new_weights: Dict[str, float]):
        """
        Update scoring weights.
        Must sum to 1.0.
        
        Args:
            new_weights: Dictionary of dimension weights
        
        Raises:
            ValueError: If weights don't sum to 1.0
        """
        if set(new_weights) != set(self.WEIGHTS):
            raise ValueError('Weights must include every scoring dimension')
        if any(weight <= 0 for weight in new_weights.values()):
            raise ValueError('Weights must be greater than zero')

        total = sum(new_weights.values())
        if not (0.99 <= total <= 1.01):  # Allow small floating point error
            raise ValueError(f"Weights must sum to 1.0, got {total}")
        
        self.weights = new_weights
        logger.info(f"Updated scoring weights: {self.weights}")
