package com.smartnote.app.data.local

import androidx.room.Embedded
import androidx.room.Relation

data class NoteWithDetails(
    @Embedded
    val note: NoteEntity,

    @Relation(
        parentColumn = "id",
        entityColumn = "noteId"
    )
    val linkItems: List<LinkItemEntity> = emptyList(),

    @Relation(
        parentColumn = "id",
        entityColumn = "noteId"
    )
    val mediaRecs: List<MediaRecEntity> = emptyList(),

    @Relation(
        parentColumn = "id",
        entityColumn = "noteId"
    )
    val flashcards: List<FlashcardEntity> = emptyList()
)
