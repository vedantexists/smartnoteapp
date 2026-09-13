package com.smartnote.app.data.local

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "media_recs",
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
data class MediaRecEntity(
    @PrimaryKey
    val id: String,
    val noteId: String,
    val title: String,
    val type: String, // Movie, Series, Song
    val creator: String,
    val reason: String
)
