from typing import List, Optional
from pydantic import BaseModel, Field

class ProfileRequest(BaseModel):
    url: str
    include_skills: bool = True
    include_experience: bool = True
    include_education: bool = True
    include_endorsements: bool = True
    include_recommendations: bool = True

class ProfileData(BaseModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    headline: Optional[str] = None
    summary: Optional[str] = None
    location: Optional[str] = None
    connections: Optional[int] = None
    followers: Optional[int] = None
    profileUrl: str

class ExperienceData(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    duration: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    description: Optional[str] = None

class EducationData(BaseModel):
    school: Optional[str] = None
    degree: Optional[str] = None
    field: Optional[str] = None
    startYear: Optional[int] = None
    endYear: Optional[int] = None

class SkillData(BaseModel):
    name: str
    endorsements: int = 0

class RecommendationData(BaseModel):
    text: str
    recommender: str

class ExtractedData(BaseModel):
    profile: ProfileData
    experience: List[ExperienceData] = []
    education: List[EducationData] = []
    skills: List[SkillData] = []
    endorsements: List[SkillData] = []
    recommendations: List[RecommendationData] = []

class ProfileResponse(BaseModel):
    success: bool
    rateLimitRemaining: int
    rateLimitReset: int
    data: Optional[ExtractedData] = None
    error: Optional[str] = None
    message: str

class UsageResponse(BaseModel):
    rateLimitRemaining: int
    rateLimitReset: int

# Router setup
from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN
from config import settings

router = APIRouter()

API_KEY_NAME = "Authorization"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if not api_key_header:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Could not validate credentials")
    
    # Check Bearer format
    parts = api_key_header.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        token = parts[1]
    else:
        token = api_key_header
        
    if token != settings.api_key:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Could not validate credentials")
    return token

@router.get("/health")
async def health_check():
    return {"status": "ok"}

@router.get("/usage", response_model=UsageResponse)
async def get_usage():
    stats = {"rateLimitRemaining": 999, "rateLimitReset": 0}
    return UsageResponse(**stats)

@router.post("/v1/profile", response_model=ProfileResponse)
async def scrape_profile(request: ProfileRequest, api_key: str = Depends(get_api_key)):
    from scraper.engine import ScraperEngine
    engine = ScraperEngine()
    stats = {"rateLimitRemaining": 999, "rateLimitReset": 0}
    
    try:
        data = await engine.scrape(request)
        
        return ProfileResponse(
            success=True,
            rateLimitRemaining=stats["rateLimitRemaining"],
            rateLimitReset=stats["rateLimitReset"],
            data=data,
            error=None,
            message="Profile scraped successfully"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        
        status_code = 500
        error_type = "Internal Server Error"
        
        if "404" in str(e):
            status_code = 404
            error_type = "Not Found"
        elif "403" in str(e) or "captcha" in str(e).lower() or "auth" in str(e).lower():
            status_code = 403
            error_type = "Forbidden"
        elif "429" in str(e) or "rate limit" in str(e).lower():
            status_code = 429
            error_type = "Too Many Requests"
            
        raise HTTPException(
            status_code=status_code,
            detail={
                "success": False,
                "rateLimitRemaining": stats["rateLimitRemaining"],
                "rateLimitReset": stats["rateLimitReset"],
                "data": None,
                "error": error_type,
                "message": str(e)
            }
        )
