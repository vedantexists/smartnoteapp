package com.smartnote.app.data.local

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import java.util.UUID

class SessionManager(context: Context) {

    companion object {
        private const val PREFS_FILE = "smartnote_encrypted_session"
        private const val KEY_USER_ID = "auth_user_id"
        private const val KEY_SESSION_TOKEN = "auth_session_token"
        private const val KEY_CONNECTED_PROVIDERS = "auth_connected_providers"
    }

    private val prefs: SharedPreferences = try {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()

        EncryptedSharedPreferences.create(
            context,
            PREFS_FILE,
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    } catch (e: Exception) {
        // Fallback to standard private mode if crypto hardware fails
        context.getSharedPreferences(PREFS_FILE, Context.MODE_PRIVATE)
    }

    fun getUserId(): String {
        var uid = prefs.getString(KEY_USER_ID, null)
        if (uid.isNullOrBlank()) {
            uid = "android_" + UUID.randomUUID().toString().replace("-", "").take(16)
            prefs.edit().putString(KEY_USER_ID, uid).apply()
        }
        return uid
    }

    fun getSessionToken(): String? {
        return prefs.getString(KEY_SESSION_TOKEN, null)
    }

    fun setSessionToken(token: String) {
        prefs.edit().putString(KEY_SESSION_TOKEN, token).apply()
    }

    fun getConnectedProviders(): Set<String> {
        return prefs.getStringSet(KEY_CONNECTED_PROVIDERS, emptySet()) ?: emptySet()
    }

    fun setConnectedProviders(providers: Set<String>) {
        prefs.edit().putStringSet(KEY_CONNECTED_PROVIDERS, providers.map { it.lowercase() }.toSet()).apply()
    }

    fun addConnectedProvider(provider: String) {
        val set = getConnectedProviders().toMutableSet()
        set.add(provider.lowercase())
        prefs.edit().putStringSet(KEY_CONNECTED_PROVIDERS, set).apply()
    }

    fun removeConnectedProvider(provider: String) {
        val set = getConnectedProviders().toMutableSet()
        set.remove(provider.lowercase())
        prefs.edit().putStringSet(KEY_CONNECTED_PROVIDERS, set).apply()
    }

    fun clearSession() {
        prefs.edit().remove(KEY_SESSION_TOKEN).remove(KEY_CONNECTED_PROVIDERS).apply()
    }
}
