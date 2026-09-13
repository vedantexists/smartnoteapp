from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Literal, Dict, Any
from enum import Enum
import datetime

class DomainCategory(str, Enum):
    TECH_EDUCATION = "TECH_EDUCATION"
    ENTERTAINMENT_REC = "ENTERTAINMENT_REC"
    EVENT = "EVENT"
    OTHER = "OTHER"

class ProcessStatus(str, Enum):
    SUCCESS = "success"
    MERGED = "merged"
    REJECTED_CLICKBAIT = "rejected_clickbait"
    FAILED = "failed"

class WebResource(BaseModel):
    name: str = Field(..., description="Name of the web tool or platform")
    url: str = Field(..., description="Direct URL of the resource")
    purpose: str = Field(..., description="What this resource does for developers/students/designers")

class EntertainmentRec(BaseModel):
    title: str = Field(..., description="Title of the movie, series, or song")
    type: Literal["Movie", "Series", "Song"] = Field(..., description="Entertainment type")
    creator: str = Field(..., description="Director, musician, or studio")
    reason: str = Field(..., description="Why it was recommended")

class Flashcard(BaseModel):
    question: str = Field(..., description="Active recall test question")
    answer: str = Field(..., description="Concise, clear answer")
    key_takeaway: Optional[str] = Field(None, description="Core principle or mnemonic")

class GeminiExtractionResult(BaseModel):
    is_clickbait_or_scam: bool = Field(
        False, 
        description="True if video is deceptive scam, pure drop-shipping promo, or empty clickbait"
    )
    clickbait_reason: Optional[str] = Field(
        None, 
        description="Explanation if marked as clickbait/scam"
    )
    domain: DomainCategory = Field(
        DomainCategory.OTHER, 
        description="High level domain classification"
    )
    title: str = Field(..., description="Clear, descriptive topic title for the note")
    core_summary: str = Field(..., description="Concise synthesis of the core topic/value")
    detailed_notes: str = Field(..., description="Structured markdown breakdown of the video content")
    flashcards: List[Flashcard] = Field(
        default_factory=list, 
        description="2-3 active recall flashcards for educational content"
    )
    github_repos: List[str] = Field(
        default_factory=list, 
        description="GitHub repos strictly formatted as owner/repo"
    )
    web_resources: List[WebResource] = Field(
        default_factory=list, 
        description="Targeted developer/student/designer web tools"
    )
    entertainment_recommendations: List[EntertainmentRec] = Field(
        default_factory=list, 
        description="Movies, series, or songs mentioned"
    )
    event_ics: Optional[str] = Field(
        None, 
        description="Raw VCALENDAR .ics format string if specific dates, webinars, or hackathons are mentioned"
    )

class IntegrationStatus(BaseModel):
    github_starred: List[str] = Field(default_factory=list)
    spotify_added: List[str] = Field(default_factory=list)
    tmdb_added: List[str] = Field(default_factory=list)
    notion_synced: bool = False
    notion_url: Optional[str] = None

class ProcessReelRequest(BaseModel):
    url: str = Field(..., description="Instagram Reel or YouTube Shorts URL")
    client_id: Optional[str] = Field(None, description="Optional Android client identifier")

class ProcessReelResponse(BaseModel):
    status: ProcessStatus
    note_id: Optional[str] = None
    message: str
    domain: Optional[DomainCategory] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    detailed_notes: Optional[str] = None
    flashcards: List[Flashcard] = Field(default_factory=list)
    github_repos: List[str] = Field(default_factory=list)
    web_resources: List[WebResource] = Field(default_factory=list)
    entertainment_recommendations: List[EntertainmentRec] = Field(default_factory=list)
    event_ics: Optional[str] = None
    integrations: IntegrationStatus = Field(default_factory=IntegrationStatus)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class NoteRecord(BaseModel):
    id: str
    source_url: str
    domain: DomainCategory
    title: str
    summary: str
    detailed_notes: str
    flashcards: List[Flashcard] = Field(default_factory=list)
    github_repos: List[str] = Field(default_factory=list)
    web_resources: List[WebResource] = Field(default_factory=list)
    entertainment_recommendations: List[EntertainmentRec] = Field(default_factory=list)
    event_ics: Optional[str] = None
    integrations: IntegrationStatus = Field(default_factory=IntegrationStatus)
    created_at: str
    updated_at: str

class SearchItem(BaseModel):
    note: NoteRecord
    similarity_score: float

class SearchResponse(BaseModel):
    query: str
    count: int
    results: List[SearchItem]

class WeeklyDigestResponse(BaseModel):
    start_date: str
    end_date: str
    total_notes_processed: int
    digest_summary: str
    top_topics: List[str]
    notable_tools: List[WebResource]
    highlight_flashcards: List[Flashcard]
    generated_at: str
