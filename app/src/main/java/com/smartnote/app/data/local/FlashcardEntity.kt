package com.smartnote.app.data.local

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "flashcards",
    foreignKeys = [
        ForeignKey(
            entity = NoteEntity::class,
            parentColumns = ["id"],
            childColumns = ["noteId"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [Index(value = ["noteId"])]
)
data class FlashcardEntity(
    @PrimaryKey
    val id: String,
    val noteId: String,
    val question: String,
    val answer: String,
    val keyTakeaway: String?,
    val reviewCount: Int = 0,
    val lastReviewedAt: Long = 0L
)
