package com.smartnote.app.data.repository

import android.content.Context
import com.google.gson.Gson
import com.smartnote.app.data.local.*
import com.smartnote.app.data.remote.RetrofitClient
import com.smartnote.app.data.remote.model.ProcessReelResponseDto
import com.smartnote.app.data.remote.model.SearchResponseDto
import com.smartnote.app.data.remote.model.WeeklyDigestResponseDto
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.withContext
import java.util.UUID

class NoteRepository(private val context: Context, private val noteDao: NoteDao) {

    private val apiService get() = RetrofitClient.getService(context)
    private val gson = Gson()

    val activeNotes: Flow<List<NoteWithDetails>> = noteDao.getAllActiveNotes()
    val allFlashcards: Flow<List<FlashcardEntity>> = noteDao.getAllFlashcards()

    fun getNotesByDomain(domain: String): Flow<List<NoteWithDetails>> = noteDao.getNotesByDomain(domain)

    fun getNoteById(id: String): Flow<NoteWithDetails?> = noteDao.getNoteByIdFlow(id)

    suspend fun recordFlashcardReview(id: String) {
        withContext(Dispatchers.IO) {
            noteDao.recordFlashcardReview(id, System.currentTimeMillis())
        }
    }

    suspend fun saveInitialProcessingNote(tempId: String, url: String) {
        withContext(Dispatchers.IO) {
            val note = NoteEntity(
                id = tempId,
                sourceUrl = url,
                domain = "PROCESSING",
                title = "Ingesting Social Video...",
                summary = "Downloading media, extracting multimodal features via Gemini, and running deduplication...",
                detailedNotes = "Video URL: $url",
                eventIcs = null,
                status = "PROCESSING",
                clickbaitReason = null,
                createdAt = System.currentTimeMillis(),
                updatedAt = System.currentTimeMillis()
            )
            noteDao.insertNote(note)
        }
    }

    suspend fun updateNoteFromApiResponse(
        response: ProcessReelResponseDto,
        fallbackId: String,
        sourceUrl: String
    ) {
        withContext(Dispatchers.IO) {
            val targetNoteId = response.noteId ?: fallbackId
            val domain = response.domain ?: "OTHER"
            val title = response.title ?: "Processed Note"
            val summary = response.summary ?: response.message
            val detailed = response.detailedNotes ?: ""

            val note = NoteEntity(
                id = targetNoteId,
                sourceUrl = sourceUrl,
                domain = domain,
                title = title,
                summary = summary,
                detailedNotes = detailed,
                eventIcs = response.eventIcs,
                status = response.status.uppercase(),
                clickbaitReason = if (response.status == "rejected_clickbait") response.summary else null,
                githubReposJson = gson.toJson(response.githubRepos),
                githubStarredJson = gson.toJson(response.integrations.githubStarred),
                spotifyAddedJson = gson.toJson(response.integrations.spotifyAdded),
                tmdbAddedJson = gson.toJson(response.integrations.tmdbAdded),
                notionSynced = response.integrations.notionSynced,
                notionUrl = response.integrations.notionUrl,
                updatedAt = System.currentTimeMillis()
            )

            val linkEntities = response.webResources.map { dto ->
                LinkItemEntity(
                    id = UUID.randomUUID().toString(),
                    noteId = targetNoteId,
                    name = dto.name,
                    url = dto.url,
                    purpose = dto.purpose
                )
            }

            val mediaRecEntities = response.entertainmentRecommendations.map { dto ->
                MediaRecEntity(
                    id = UUID.randomUUID().toString(),
                    noteId = targetNoteId,
                    title = dto.title,
                    type = dto.type,
                    creator = dto.creator,
                    reason = dto.reason
                )
            }

            val flashcardEntities = response.flashcards.map { dto ->
                FlashcardEntity(
                    id = UUID.randomUUID().toString(),
                    noteId = targetNoteId,
                    question = dto.question,
                    answer = dto.answer,
                    keyTakeaway = dto.keyTakeaway
                )
            }

            // Upsert full note
            noteDao.upsertFullNote(note, linkEntities, mediaRecEntities, flashcardEntities)

            // If this was a merge into an existing note, remove the temporary processing note if IDs differ
            if (response.status == "merged" && targetNoteId != fallbackId) {
                noteDao.deleteNoteById(fallbackId)
            }
        }
    }

    suspend fun markNoteFailed(noteId: String, errorMessage: String) {
        withContext(Dispatchers.IO) {
            val existing = noteDao.getNoteById(noteId)
            if (existing != null) {
                val updated = existing.note.copy(
                    status = "FAILED",
                    summary = "Processing failed: $errorMessage",
                    updatedAt = System.currentTimeMillis()
                )
                noteDao.updateNote(updated)
            }
        }
    }

    suspend fun searchRemote(query: String): Result<SearchResponseDto> {
        return withContext(Dispatchers.IO) {
            try {
                val resp = apiService.searchNotes(query)
                if (resp.isSuccessful && resp.body() != null) {
                    Result.success(resp.body()!!)
                } else {
                    Result.failure(Exception("Search failed with HTTP ${resp.code()}"))
                }
            } catch (e: Exception) {
                Result.failure(e)
            }
        }
    }

    suspend fun fetchWeeklyDigest(forceRefresh: Boolean = false): Result<WeeklyDigestResponseDto> {
        return withContext(Dispatchers.IO) {
            try {
                val resp = apiService.getWeeklyDigest(forceRefresh)
                if (resp.isSuccessful && resp.body() != null) {
                    Result.success(resp.body()!!)
                } else {
                    Result.failure(Exception("Failed to fetch digest: HTTP ${resp.code()}"))
                }
            } catch (e: Exception) {
                Result.failure(e)
            }
        }
    }
}
