package com.smartnote.app.data.local

import androidx.room.*
import kotlinx.coroutines.flow.Flow

@Dao
interface NoteDao {

    @Transaction
    @Query("SELECT * FROM notes WHERE status != 'REJECTED_CLICKBAIT' ORDER BY updatedAt DESC")
    fun getAllActiveNotes(): Flow<List<NoteWithDetails>>

    @Transaction
    @Query("SELECT * FROM notes ORDER BY updatedAt DESC")
    fun getAllNotes(): Flow<List<NoteWithDetails>>

    @Transaction
    @Query("SELECT * FROM notes WHERE domain = :domain AND status != 'REJECTED_CLICKBAIT' ORDER BY updatedAt DESC")
    fun getNotesByDomain(domain: String): Flow<List<NoteWithDetails>>

    @Transaction
    @Query("SELECT * FROM notes WHERE id = :id LIMIT 1")
    suspend fun getNoteById(id: String): NoteWithDetails?

    @Transaction
    @Query("SELECT * FROM notes WHERE id = :id LIMIT 1")
    fun getNoteByIdFlow(id: String): Flow<NoteWithDetails?>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertNote(note: NoteEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertLinkItems(links: List<LinkItemEntity>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertMediaRecs(recs: List<MediaRecEntity>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertFlashcards(cards: List<FlashcardEntity>)

    @Update
    suspend fun updateNote(note: NoteEntity)

    @Query("DELETE FROM link_items WHERE noteId = :noteId")
    suspend fun deleteLinkItemsByNoteId(noteId: String)

    @Query("DELETE FROM media_recs WHERE noteId = :noteId")
    suspend fun deleteMediaRecsByNoteId(noteId: String)

    @Query("DELETE FROM flashcards WHERE noteId = :noteId")
    suspend fun deleteFlashcardsByNoteId(noteId: String)

    @Query("SELECT * FROM flashcards ORDER BY lastReviewedAt ASC")
    fun getAllFlashcards(): Flow<List<FlashcardEntity>>

    @Query("UPDATE flashcards SET reviewCount = reviewCount + 1, lastReviewedAt = :timestamp WHERE id = :id")
    suspend fun recordFlashcardReview(id: String, timestamp: Long)

    @Transaction
    suspend fun upsertFullNote(
        note: NoteEntity,
        links: List<LinkItemEntity>,
        recs: List<MediaRecEntity>,
        cards: List<FlashcardEntity>
    ) {
        insertNote(note)
        // Clean out old relations for updated / merged notes to avoid orphaned duplicates
        deleteLinkItemsByNoteId(note.id)
        deleteMediaRecsByNoteId(note.id)
        deleteFlashcardsByNoteId(note.id)

        if (links.isNotEmpty()) insertLinkItems(links)
        if (recs.isNotEmpty()) insertMediaRecs(recs)
        if (cards.isNotEmpty()) insertFlashcards(cards)
    }

    @Query("DELETE FROM notes WHERE id = :id")
    suspend fun deleteNoteById(id: String)
}
