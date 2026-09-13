package com.smartnote.app.ui.screens

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.Toast
import androidx.browser.customtabs.CustomTabsIntent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.smartnote.app.data.remote.RetrofitClient
import com.smartnote.app.data.repository.NoteRepository
import com.smartnote.app.ui.theme.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@Composable
fun SettingsScreen(
    repository: NoteRepository,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var baseUrl by remember { mutableStateOf(RetrofitClient.getBaseUrl(context)) }
    var connectionStatus by remember { mutableStateOf<String?>(null) }
    var isChecking by remember { mutableStateOf(false) }

    val sessionManager = repository.sessionManager
    var connectedProviders by remember { mutableStateOf(sessionManager.getConnectedProviders()) }
    var isRefreshingAuth by remember { mutableStateOf(false) }
    var disconnectingProvider by remember { mutableStateOf<String?>(null) }

    // Synchronize initial auth status with backend on screen mount
    LaunchedEffect(Unit) {
        scope.launch {
            repository.fetchAuthStatus().onSuccess { providers ->
                connectedProviders = providers.map { it.lowercase() }.toSet()
            }
        }
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(BackgroundDark)
            .padding(16.dp)
            .verticalScroll(rememberScrollState())
    ) {
        Spacer(modifier = Modifier.height(16.dp))

        Text(
            text = "Settings & Integrations",
            color = TextPrimaryDark,
            fontSize = 20.sp,
            fontWeight = FontWeight.Bold
        )
        Text(
            text = "Multi-tenant OAuth2 with PKCE, encrypted sessions, and backend configuration",
            color = TextMutedDark,
            fontSize = 12.sp
        )

        Spacer(modifier = Modifier.height(20.dp))

        // OAuth2 Cloud Accounts Card
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(containerColor = SurfaceDark),
            border = CardDefaults.outlinedCardBorder().copy(brush = androidx.compose.ui.graphics.SolidColor(CardBorderDark))
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text(
                            text = "🔐 Connected Integrations (OAuth2 PKCE)",
                            color = PrimaryIndigo,
                            fontWeight = FontWeight.Bold,
                            fontSize = 14.sp
                        )
                        Text(
                            text = "No manual Personal Access Tokens required. Tokens encrypted at rest.",
                            color = TextSecondaryDark,
                            fontSize = 11.sp
                        )
                    }

                    IconButton(
                        onClick = {
                            isRefreshingAuth = true
                            scope.launch {
                                repository.fetchAuthStatus()
                                    .onSuccess { providers ->
                                        connectedProviders = providers.map { it.lowercase() }.toSet()
                                        Toast.makeText(context, "Status refreshed", Toast.LENGTH_SHORT).show()
                                    }
                                    .onFailure {
                                        Toast.makeText(context, "Failed to refresh status: ${it.localizedMessage}", Toast.LENGTH_SHORT).show()
                                    }
                                isRefreshingAuth = false
                            }
                        }
                    ) {
                        if (isRefreshingAuth) {
                            CircularProgressIndicator(modifier = Modifier.size(16.dp), color = PrimaryIndigo)
                        } else {
                            Text("🔄", fontSize = 14.sp)
                        }
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))

                // GitHub OAuth Row
                val isGitHubConnected = connectedProviders.contains("github")
                OAuthProviderRow(
                    name = "GitHub",
                    icon = "⭐",
                    description = "Auto-stars referenced open source repositories",
                    isConnected = isGitHubConnected,
                    isLoading = disconnectingProvider == "github",
                    onConnect = {
                        val userId = sessionManager.getUserId()
                        val url = "${baseUrl.trimEnd('/')}/auth/github/login?user_id=$userId"
                        launchChromeCustomTab(context, url)
                    },
                    onDisconnect = {
                        disconnectingProvider = "github"
                        scope.launch {
                            repository.disconnectProvider("github")
                                .onSuccess {
                                    connectedProviders = sessionManager.getConnectedProviders()
                                    Toast.makeText(context, "Disconnected GitHub", Toast.LENGTH_SHORT).show()
                                }
                                .onFailure {
                                    Toast.makeText(context, "Failed to disconnect: ${it.localizedMessage}", Toast.LENGTH_SHORT).show()
                                }
                            disconnectingProvider = null
                        }
                    }
                )

                HorizontalDivider(
                    modifier = Modifier.padding(vertical = 12.dp),
                    color = CardBorderDark
                )

                // Spotify OAuth Row
                val isSpotifyConnected = connectedProviders.contains("spotify")
                OAuthProviderRow(
                    name = "Spotify",
                    icon = "🎵",
                    description = "Adds soundtrack & songs discovered in Reels to your playlist",
                    isConnected = isSpotifyConnected,
                    isLoading = disconnectingProvider == "spotify",
                    onConnect = {
                        val userId = sessionManager.getUserId()
                        val url = "${baseUrl.trimEnd('/')}/auth/spotify/login?user_id=$userId"
                        launchChromeCustomTab(context, url)
                    },
                    onDisconnect = {
                        disconnectingProvider = "spotify"
                        scope.launch {
                            repository.disconnectProvider("spotify")
                                .onSuccess {
                                    connectedProviders = sessionManager.getConnectedProviders()
                                    Toast.makeText(context, "Disconnected Spotify", Toast.LENGTH_SHORT).show()
                                }
                                .onFailure {
                                    Toast.makeText(context, "Failed to disconnect: ${it.localizedMessage}", Toast.LENGTH_SHORT).show()
                                }
                            disconnectingProvider = null
                        }
                    }
                )
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Backend URL Config Card
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(containerColor = SurfaceDark),
            border = CardDefaults.outlinedCardBorder().copy(brush = androidx.compose.ui.graphics.SolidColor(CardBorderDark))
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "Backend API URL",
                    color = PrimaryIndigo,
                    fontWeight = FontWeight.Bold,
                    fontSize = 14.sp
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = "Enter your Hugging Face Space URL or local dev server (e.g. http://10.0.2.2:7860/)",
                    color = TextSecondaryDark,
                    fontSize = 11.sp
                )

                Spacer(modifier = Modifier.height(12.dp))

                OutlinedTextField(
                    value = baseUrl,
                    onValueChange = { baseUrl = it },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    shape = RoundedCornerShape(10.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = PrimaryIndigo,
                        unfocusedBorderColor = CardBorderDark,
                        focusedTextColor = TextPrimaryDark,
                        unfocusedTextColor = TextPrimaryDark
                    )
                )

                Spacer(modifier = Modifier.height(12.dp))

                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(
                        onClick = {
                            RetrofitClient.setBaseUrl(context, baseUrl)
                            Toast.makeText(context, "Saved API URL", Toast.LENGTH_SHORT).show()
                        },
                        colors = ButtonDefaults.buttonColors(containerColor = PrimaryIndigo),
                        shape = RoundedCornerShape(10.dp)
                    ) {
                        Text("Save URL")
                    }

                    OutlinedButton(
                        onClick = {
                            isChecking = true
                            connectionStatus = null
                            scope.launch {
                                try {
                                    val service = RetrofitClient.getService(context)
                                    val resp = withContext(Dispatchers.IO) { service.checkHealth() }
                                    isChecking = false
                                    if (resp.isSuccessful) {
                                        val body = resp.body()
                                        connectionStatus = "Connected! Backend healthy (Model: ${body?.get("gemini_model")})"
                                    } else {
                                        connectionStatus = "Failed: HTTP ${resp.code()}"
                                    }
                                } catch (e: Exception) {
                                    isChecking = false
                                    connectionStatus = "Error: ${e.localizedMessage}"
                                }
                            }
                        },
                        shape = RoundedCornerShape(10.dp),
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = AccentEmerald)
                    ) {
                        if (isChecking) {
                            CircularProgressIndicator(modifier = Modifier.size(16.dp), color = AccentEmerald)
                        } else {
                            Text("Test Health")
                        }
                    }
                }

                if (connectionStatus != null) {
                    Spacer(modifier = Modifier.height(10.dp))
                    Text(
                        text = connectionStatus!!,
                        color = if (connectionStatus!!.startsWith("Connected")) AccentEmerald else AccentRose,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Medium
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Device Optimization Card (Universal Android OEM Battery Optimization)
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(containerColor = SurfaceDark),
            border = CardDefaults.outlinedCardBorder().copy(brush = androidx.compose.ui.graphics.SolidColor(CardBorderDark))
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "📱 Universal Device Optimization",
                    color = AccentAmber,
                    fontWeight = FontWeight.Bold,
                    fontSize = 14.sp
                )
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = "Resilient Background Sync (Android 7.0+ / API 24–34+)",
                    color = TextPrimaryDark,
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 13.sp
                )
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = "SmartNote utilizes AndroidX WorkManager with exponential backoff constraints, encrypted session storage, and network type guarantees. When you share a Reel or Short, the task is persisted to system SQLite and processed reliably in the background without UI blocking, surviving aggressive OEM battery optimizers (Samsung OneUI, Xiaomi MIUI/HyperOS, OnePlus/Oppo ColorOS).",
                    color = TextSecondaryDark,
                    fontSize = 12.sp,
                    lineHeight = 17.sp
                )
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Integration Status Summary Card
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(containerColor = SurfaceDark),
            border = CardDefaults.outlinedCardBorder().copy(brush = androidx.compose.ui.graphics.SolidColor(CardBorderDark))
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "⚡ Automated Free-Tier Integrations",
                    color = AccentSky,
                    fontWeight = FontWeight.Bold,
                    fontSize = 14.sp
                )
                Spacer(modifier = Modifier.height(8.dp))
                Text("• ⭐ GitHub: Stars repositories securely via OAuth2 PKCE token exchange.", color = TextSecondaryDark, fontSize = 12.sp)
                Text("• 🎵 Spotify: Appends discovered songs to your Spotify playlist via OAuth2 PKCE.", color = TextSecondaryDark, fontSize = 12.sp)
                Text("• 🎬 TMDB: Adds movies/series to your TMDB watchlist.", color = TextSecondaryDark, fontSize = 12.sp)
                Text("• 📝 Notion: Appends structured notes and flashcards to Notion.", color = TextSecondaryDark, fontSize = 12.sp)
                Text("• 📅 Calendar: Generates native .ics files for one-tap imports.", color = TextSecondaryDark, fontSize = 12.sp)
            }
        }

        Spacer(modifier = Modifier.height(24.dp))
    }
}

@Composable
fun OAuthProviderRow(
    name: String,
    icon: String,
    description: String,
    isConnected: Boolean,
    isLoading: Boolean,
    onConnect: () -> Unit,
    onDisconnect: () -> Unit
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Row(
            modifier = Modifier.weight(1f),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Text(text = icon, fontSize = 20.sp)
            Column {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text(
                        text = name,
                        color = TextPrimaryDark,
                        fontWeight = FontWeight.Bold,
                        fontSize = 14.sp
                    )
                    Surface(
                        color = if (isConnected) AccentEmerald.copy(alpha = 0.15f) else Color.DarkGray.copy(alpha = 0.4f),
                        shape = RoundedCornerShape(6.dp)
                    ) {
                        Text(
                            text = if (isConnected) "Connected" else "Not Linked",
                            color = if (isConnected) AccentEmerald else TextMutedDark,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.SemiBold,
                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                        )
                    }
                }
                Text(
                    text = description,
                    color = TextMutedDark,
                    fontSize = 11.sp,
                    lineHeight = 14.sp
                )
            }
        }

        Spacer(modifier = Modifier.width(8.dp))

        if (isLoading) {
            CircularProgressIndicator(modifier = Modifier.size(20.dp), color = PrimaryIndigo)
        } else if (isConnected) {
            OutlinedButton(
                onClick = onDisconnect,
                colors = ButtonDefaults.outlinedButtonColors(contentColor = AccentRose),
                shape = RoundedCornerShape(8.dp),
                contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp)
            ) {
                Text("Disconnect", fontSize = 12.sp)
            }
        } else {
            Button(
                onClick = onConnect,
                colors = ButtonDefaults.buttonColors(containerColor = PrimaryIndigo),
                shape = RoundedCornerShape(8.dp),
                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp)
            ) {
                Text("Connect", fontSize = 12.sp)
            }
        }
    }
}

fun launchChromeCustomTab(context: Context, url: String) {
    try {
        val customTabsIntent = CustomTabsIntent.Builder()
            .setShowTitle(true)
            .build()
        customTabsIntent.launchUrl(context, Uri.parse(url))
    } catch (e: Exception) {
        // Fallback to standard browser intent
        val browserIntent = Intent(Intent.ACTION_VIEW, Uri.parse(url)).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        }
        context.startActivity(browserIntent)
    }
}
