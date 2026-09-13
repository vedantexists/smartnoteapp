package com.smartnote.app.data.remote

import android.content.Context
import android.content.SharedPreferences
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object RetrofitClient {

    private const val PREFS_NAME = "smartnote_prefs"
    private const val KEY_BASE_URL = "backend_base_url"
    // Default URL: Supports local dev or Hugging Face Space URL
    const val DEFAULT_BASE_URL = "http://10.0.2.2:7860/"

    @Volatile
    private var serviceInstance: SmartNoteApiService? = null
    private var currentBaseUrl: String? = null

    fun getBaseUrl(context: Context): String {
        val prefs: SharedPreferences = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        return prefs.getString(KEY_BASE_URL, DEFAULT_BASE_URL) ?: DEFAULT_BASE_URL
    }

    fun setBaseUrl(context: Context, newUrl: String) {
        val formatted = if (newUrl.endsWith("/")) newUrl else "$newUrl/"
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_BASE_URL, formatted)
            .apply()
        synchronized(this) {
            serviceInstance = null
            currentBaseUrl = null
        }
    }

    fun getService(context: Context): SmartNoteApiService {
        val baseUrl = getBaseUrl(context)
        return if (serviceInstance != null && currentBaseUrl == baseUrl) {
            serviceInstance!!
        } else {
            synchronized(this) {
                currentBaseUrl = baseUrl
                val logging = HttpLoggingInterceptor().apply {
                    level = HttpLoggingInterceptor.Level.BODY
                }

                val okHttpClient = OkHttpClient.Builder()
                    .addInterceptor(logging)
                    .connectTimeout(60, TimeUnit.SECONDS)
                    .readTimeout(180, TimeUnit.SECONDS) // Gemini multimodal processing may take up to 2 minutes
                    .writeTimeout(60, TimeUnit.SECONDS)
                    .retryOnConnectionFailure(true)
                    .build()

                val retrofit = Retrofit.Builder()
                    .baseUrl(baseUrl)
                    .client(okHttpClient)
                    .addConverterFactory(GsonConverterFactory.create())
                    .build()

                val service = retrofit.create(SmartNoteApiService::class.java)
                serviceInstance = service
                service
            }
        }
    }
}
