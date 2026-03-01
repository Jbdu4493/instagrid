from typing import List, Optional
from pydantic import BaseModel

class HashtagLadder(BaseModel):
    broad: List[str]
    niche: List[str]
    specific: List[str]

class AnalysisResponse(BaseModel):
    suggested_order: List[int] 
    captions: List[str] 
    individual_scores: List[int]
    hashtags: List[HashtagLadder]
    coherence_score: int
    coherence_reasoning: str
    common_thread_fr: Optional[str] = ""
    common_thread_en: Optional[str] = ""

class PostItem(BaseModel):
    image_base64: str
    caption: str

class PostRequest(BaseModel):
    access_token: Optional[str] = None
    ig_user_id: Optional[str] = None
    posts: List[PostItem] 

class RegenerateRequest(BaseModel):
    image_base64: str
    common_context: Optional[str] = ""
    individual_context: Optional[str] = ""
    captions_history: List[str] = []
    common_thread_fr: Optional[str] = ""
    common_thread_en: Optional[str] = ""
    ai_provider: Optional[str] = "openai"

class RegenerateResponseParts(BaseModel):
    specific_fr: str
    specific_en: str

class RegenerateResponse(BaseModel):
    caption: str

class TokenExchangeRequest(BaseModel):
    short_lived_token: str

class SaveDraftRequest(BaseModel):
    posts: List[PostItem]
    crop_ratios: Optional[List[str]] = None
    crop_positions: Optional[List[dict]] = None

class UpdateDraftRequest(BaseModel):
    captions: Optional[List[str]] = None
    crop_ratios: Optional[List[str]] = None
    crop_positions: Optional[List[dict]] = None
    post_order: Optional[List[int]] = None

class PostDraftRequest(BaseModel):
    access_token: Optional[str] = None
    ig_user_id: Optional[str] = None
    force: bool = False  # Set to True to re-post an already posted draft
