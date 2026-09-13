package com.smartnote.app.data.remote.model

import com.google.gson.annotations.SerializedName

data class ProcessReelRequestDto(
    @SerializedName("url") val url: String,
    @SerializedName("client_id") val clientId: String? = null
)

data class WebResourceDto(
    @SerializedName("name") val name: String,
    @SerializedName("url") val url: String,
    @SerializedName("purpose") val purpose: String
)

data class EntertainmentRecDto(
    @SerializedName("title") val title: String,
    @SerializedName("type") val type: String,
    @SerializedName("creator") val creator: String,
    @SerializedName("reason") val reason: String
)

data class FlashcardDto(
    @SerializedName("question") val question: String,
    @SerializedName("answer") val answer: String,
    @SerializedName("key_takeaway") val keyTakeaway: String? = null
)

data class IntegrationStatusDto(
    @SerializedName("github_starred") val githubStarred: List<String> = emptyList(),
    @SerializedName("spotify_added") val spotifyAdded: List<String> = emptyList(),
    @SerializedName("tmdb_added") val tmdbAdded: List<String> = emptyList(),
    @SerializedName("notion_synced") val notionSynced: Boolean = false,
    @SerializedName("notion_url") val notionUrl: String? = null
)

data class ProcessReelResponseDto(
    @SerializedName("status") val status: String,
    @SerializedName("note_id") val noteId: String?,
    @SerializedName("message") val message: String,
    @SerializedName("domain") val domain: String?,
    @SerializedName("title") val title: String?,
    @SerializedName("summary") val summary: String?,
    @SerializedName("detailed_notes") val detailedNotes: String?,
    @SerializedName("flashcards") val flashcards: List<FlashcardDto> = emptyList(),
    @SerializedName("github_repos") val githubRepos: List<String> = emptyList(),
    @SerializedName("web_resources") val webResources: List<WebResourceDto> = emptyList(),
    @SerializedName("entertainment_recommendations") val entertainmentRecommendations: List<EntertainmentRecDto> = emptyList(),
    @SerializedName("event_ics") val eventIcs: String? = null,
    @SerializedName("integrations") val integrations: IntegrationStatusDto = IntegrationStatusDto(),
    @SerializedName("created_at") val createdAt: String? = null,
    @SerializedName("updated_at") val updatedAt: String? = null
)

data class NoteRecordDto(
    @SerializedName("id") val id: String,
    @SerializedName("source_url") val sourceUrl: String,
    @SerializedName("domain") val domain: String,
    @SerializedName("title") val title: String,
    @SerializedName("summary") val summary: String,
    @SerializedName("detailed_notes") val detailedNotes: String,
    @SerializedName("flashcards") val flashcards: List<FlashcardDto> = emptyList(),
    @SerializedName("github_repos") val githubRepos: List<String> = emptyList(),
    @SerializedName("web_resources") val webResources: List<WebResourceDto> = emptyList(),
    @SerializedName("entertainment_recommendations") val entertainmentRecommendations: List<EntertainmentRecDto> = emptyList(),
    @SerializedName("event_ics") val eventIcs: String? = null,
    @SerializedName("integrations") val integrations: IntegrationStatusDto = IntegrationStatusDto(),
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("updated_at") val updatedAt: String
)

data class SearchItemDto(
    @SerializedName("note") val note: NoteRecordDto,
    @SerializedName("similarity_score") val similarityScore: Float
)

data class SearchResponseDto(
    @SerializedName("query") val query: String,
    @SerializedName("count") val count: Int,
    @SerializedName("results") val results: List<SearchItemDto>
)

data class WeeklyDigestResponseDto(
    @SerializedName("start_date") val startDate: String,
    @SerializedName("end_date") val endDate: String,
    @SerializedName("total_notes_processed") val totalNotesProcessed: Int,
    @SerializedName("digest_summary") val digestSummary: String,
    @SerializedName("top_topics") val topTopics: List<String> = emptyList(),
    @SerializedName("notable_tools") val notableTools: List<WebResourceDto> = emptyList(),
    @SerializedName("highlight_flashcards") val highlightFlashcards: List<FlashcardDto> = emptyList(),
    @SerializedName("generated_at") val generatedAt: String
)

data class SessionResponseDto(
    @SerializedName("user_id") val userId: String,
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("token_type") val tokenType: String,
    @SerializedName("expires_in_days") val expiresInDays: Int
)

data class AuthStatusResponseDto(
    @SerializedName("user_id") val userId: String,
    @SerializedName("connected_providers") val connectedProviders: List<String> = emptyList()
)
