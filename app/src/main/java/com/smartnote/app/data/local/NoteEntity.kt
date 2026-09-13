package com.smartnote.app.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "notes")
data class NoteEntity(
    @PrimaryKey
    val id: String,
    val sourceUrl: String,
    val domain: String, // TECH_EDUCATION, ENTERTAINMENT_REC, EVENT, OTHER
    val title: String,
    val summary: String,
    val detailedNotes: String,
    val eventIcs: String?,
    val status: String, // "PROCESSING", "SUCCESS", "MERGED", "REJECTED_CLICKBAIT", "FAILED"
    val clickbaitReason: String?,
    val githubReposJson: String = "[]",
    val githubStarredJson: String = "[]",
    val spotifyAddedJson: String = "[]",
    val tmdbAddedJson: String = "[]",
    val notionSynced: Boolean = false,
    val notionUrl: String? = null,
    val createdAt: Long = System.currentTimeMillis(),
    val updatedAt: Long = System.currentTimeMillis()
)
