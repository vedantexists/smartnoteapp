package com.smartnote.app.data.remote

import com.smartnote.app.data.remote.model.*
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query

interface SmartNoteApiService {

    @POST("process-reel")
    suspend fun processReel(@Body request: ProcessReelRequestDto): Response<ProcessReelResponseDto>

    @GET("search")
    suspend fun searchNotes(@Query("q") query: String): Response<SearchResponseDto>

    @GET("digest/weekly")
    suspend fun getWeeklyDigest(@Query("force_refresh") forceRefresh: Boolean = false): Response<WeeklyDigestResponseDto>

    @GET("notes")
    suspend fun getNotes(
        @Query("limit") limit: Int = 50,
        @Query("offset") offset: Int = 0,
        @Query("domain") domain: String? = null
    ): Response<List<NoteRecordDto>>

    @GET("health")
    suspend fun checkHealth(): Response<Map<String, Any>>

    @POST("auth/session")
    suspend fun createSession(@Query("user_id") userId: String? = null): Response<SessionResponseDto>

    @GET("auth/status")
    suspend fun getAuthStatus(): Response<AuthStatusResponseDto>

    @retrofit2.http.DELETE("auth/{provider}")
    suspend fun disconnectProvider(@retrofit2.http.Path("provider") provider: String): Response<Map<String, Any>>
}
