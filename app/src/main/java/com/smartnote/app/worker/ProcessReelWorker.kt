package com.smartnote.app.worker

import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import androidx.core.app.NotificationCompat
import androidx.work.*
import com.smartnote.app.SmartNoteApp
import com.smartnote.app.data.local.AppDatabase
import com.smartnote.app.data.remote.RetrofitClient
import com.smartnote.app.data.remote.model.ProcessReelRequestDto
import com.smartnote.app.data.repository.NoteRepository
import com.smartnote.app.ui.MainActivity
import java.util.UUID
import java.util.concurrent.TimeUnit

class ProcessReelWorker(
    context: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(context, workerParams) {

    companion object {
        const val KEY_URL = "extra_reel_url"
        const val KEY_TEMP_ID = "extra_temp_id"
        private const val UNIQUE_WORK_NAME_PREFIX = "process_reel_"

        /**
         * Enqueues background worker with network constraints and exponential backoff,
         * ensuring survival on aggressive battery optimization engines across OEM devices.
         */
        fun enqueue(context: Context, url: String): String {
            val tempId = UUID.randomUUID().toString()

            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()

            val inputData = Data.Builder()
                .putString(KEY_URL, url)
                .putString(KEY_TEMP_ID, tempId)
                .build()

            val workRequest = OneTimeWorkRequestBuilder<ProcessReelWorker>()
                .setConstraints(constraints)
                .setInputData(inputData)
                .setBackoffCriteria(
                    BackoffPolicy.EXPONENTIAL,
                    15,
                    TimeUnit.SECONDS
                )
                .build()

            WorkManager.getInstance(context)
                .enqueueUniqueWork(
                    "$UNIQUE_WORK_NAME_PREFIX$tempId",
                    ExistingWorkPolicy.REPLACE,
                    workRequest
                )

            return tempId
        }
    }

    override suspend fun doWork(): Result {
        val url = inputData.getString(KEY_URL) ?: return Result.failure()
        val tempId = inputData.getString(KEY_TEMP_ID) ?: UUID.randomUUID().toString()

        val db = AppDatabase.getDatabase(applicationContext)
        val repository = NoteRepository(applicationContext, db.noteDao())
        val apiService = RetrofitClient.getService(applicationContext)

        try {
            // Save initial processing note state in Room
            repository.saveInitialProcessingNote(tempId, url)

            // Ensure encrypted session and JWT bearer token are active
            repository.ensureSessionInitialized()

            // Make POST request to backend /process-reel
            val response = apiService.processReel(ProcessReelRequestDto(url = url, clientId = tempId))

            if (response.isSuccessful && response.body() != null) {
                val dto = response.body()!!

                // Update local Room database
                repository.updateNoteFromApiResponse(dto, fallbackId = tempId, sourceUrl = url)

                // Trigger Android notification
                val title = dto.title ?: "Social Video Processed"
                val message = when (dto.status.lowercase()) {
                    "merged" -> "⚡ Merged with existing note: ${dto.title}"
                    "rejected_clickbait" -> "⚠️ Flagged as clickbait/scam: ${dto.title}"
                    else -> "✅ New note saved: ${dto.title}"
                }
                showCompletionNotification(title, message)

                return Result.success()
            } else {
                val errorMsg = "HTTP ${response.code()}: ${response.errorBody()?.string() ?: "Unknown error"}"
                if (runAttemptCount < 3) {
                    return Result.retry()
                } else {
                    repository.markNoteFailed(tempId, errorMsg)
                    return Result.failure()
                }
            }
        } catch (e: Exception) {
            if (runAttemptCount < 3) {
                return Result.retry()
            } else {
                repository.markNoteFailed(tempId, e.localizedMessage ?: "Network error")
                return Result.failure()
            }
        }
    }

    private fun showCompletionNotification(title: String, message: String) {
        val intent = Intent(applicationContext, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        }
        val pendingIntent = PendingIntent.getActivity(
            applicationContext,
            0,
            intent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        val notification = NotificationCompat.Builder(applicationContext, SmartNoteApp.CHANNEL_ID)
            .setSmallIcon(android.R.drawable.stat_notify_chat)
            .setContentTitle(title)
            .setContentText(message)
            .setStyle(NotificationCompat.BigTextStyle().bigText(message))
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .setContentIntent(pendingIntent)
            .setAutoCancel(true)
            .build()

        val notificationManager =
            applicationContext.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        notificationManager.notify(System.currentTimeMillis().toInt(), notification)
    }
}
