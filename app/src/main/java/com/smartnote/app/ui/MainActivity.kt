package com.smartnote.app.ui

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.Psychology
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.core.content.ContextCompat
import com.smartnote.app.R
import com.smartnote.app.SmartNoteApp
import com.smartnote.app.data.repository.NoteRepository
import com.smartnote.app.ui.screens.DigestScreen
import com.smartnote.app.ui.screens.FlashcardsScreen
import com.smartnote.app.ui.screens.NotesFeedScreen
import com.smartnote.app.ui.screens.SettingsScreen
import com.smartnote.app.ui.theme.PrimaryIndigo
import com.smartnote.app.ui.theme.SmartNoteTheme
import com.smartnote.app.ui.theme.SurfaceDark
import com.smartnote.app.ui.theme.TextMutedDark
import com.smartnote.app.worker.ProcessReelWorker
import java.util.regex.Pattern

class MainActivity : ComponentActivity() {

    private lateinit var repository: NoteRepository

    private val notificationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { _ -> }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val app = application as SmartNoteApp
        repository = NoteRepository(this, app.database.noteDao())

        // Request notification permission for Android 13+
        requestNotificationPermission()

        // Handle incoming shared social video URL if launched via Android Share Sheet
        handleIncomingIntent(intent)

        setContent {
            SmartNoteTheme {
                MainAppScaffold(repository = repository)
            }
        }
    }

    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        intent?.let { handleIncomingIntent(it) }
    }

    private fun handleIncomingIntent(intent: Intent) {
        // Handle OAuth2 PKCE redirect deep links: reelnotes://auth/callback?status=success&provider=github
        if (Intent.ACTION_VIEW == intent.action && intent.data != null) {
            val uri = intent.data!!
            if (uri.scheme == "reelnotes" && uri.host == "auth" && uri.path == "/callback") {
                val status = uri.getQueryParameter("status") ?: "unknown"
                val provider = uri.getQueryParameter("provider") ?: ""
                val message = uri.getQueryParameter("message")

                if (status.equals("success", ignoreCase = true)) {
                    if (provider.isNotBlank()) {
                        repository.sessionManager.addConnectedProvider(provider)
                        Toast.makeText(
                            this,
                            "Connected to ${provider.replaceFirstChar { it.uppercase() }} successfully!",
                            Toast.LENGTH_LONG
                        ).show()
                    }
                } else {
                    val detail = if (!message.isNullOrBlank()) ": $message" else ""
                    Toast.makeText(
                        this,
                        "Authentication for $provider $status$detail",
                        Toast.LENGTH_LONG
                    ).show()
                }
                return
            }
        }

        // Handle incoming shared social video URL if launched via Android Share Sheet
        if (Intent.ACTION_SEND == intent.action && intent.type == "text/plain") {
            val sharedText = intent.getStringExtra(Intent.EXTRA_TEXT) ?: return
            val extractedUrl = extractUrl(sharedText)

            if (extractedUrl != null) {
                // Enqueue background processing worker
                ProcessReelWorker.enqueue(this, extractedUrl)
                Toast.makeText(this, getString(R.string.share_received), Toast.LENGTH_LONG).show()
            } else {
                Toast.makeText(this, "No valid video URL detected in shared text", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun extractUrl(text: String): String? {
        val urlPattern = Pattern.compile(
            "https?://(?:www\\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_+.~#?&/=]*)"
        )
        val matcher = urlPattern.matcher(text)
        return if (matcher.find()) {
            matcher.group(0)
        } else null
    }

    private fun requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(
                    this,
                    Manifest.permission.POST_NOTIFICATIONS
                ) != PackageManager.PERMISSION_GRANTED
            ) {
                notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
            }
        }
    }
}

enum class NavTab {
    FEED, FLASHCARDS, DIGEST, SETTINGS
}

@Composable
fun MainAppScaffold(repository: NoteRepository) {
    var currentTab by remember { mutableStateOf(NavTab.FEED) }

    Scaffold(
        modifier = Modifier.fillMaxSize(),
        bottomBar = {
            NavigationBar(
                containerColor = SurfaceDark
            ) {
                NavigationBarItem(
                    selected = currentTab == NavTab.FEED,
                    onClick = { currentTab = NavTab.FEED },
                    icon = { Icon(Icons.Default.Description, contentDescription = "Notes") },
                    label = { Text("Notes") },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = PrimaryIndigo,
                        selectedTextColor = PrimaryIndigo,
                        unselectedIconColor = TextMutedDark,
                        unselectedTextColor = TextMutedDark,
                        indicatorColor = PrimaryIndigo.copy(alpha = 0.2f)
                    )
                )
                NavigationBarItem(
                    selected = currentTab == NavTab.FLASHCARDS,
                    onClick = { currentTab = NavTab.FLASHCARDS },
                    icon = { Icon(Icons.Default.Psychology, contentDescription = "Flashcards") },
                    label = { Text("Cards") },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = PrimaryIndigo,
                        selectedTextColor = PrimaryIndigo,
                        unselectedIconColor = TextMutedDark,
                        unselectedTextColor = TextMutedDark,
                        indicatorColor = PrimaryIndigo.copy(alpha = 0.2f)
                    )
                )
                NavigationBarItem(
                    selected = currentTab == NavTab.DIGEST,
                    onClick = { currentTab = NavTab.DIGEST },
                    icon = { Icon(Icons.Default.CalendarMonth, contentDescription = "Digest") },
                    label = { Text("Digest") },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = PrimaryIndigo,
                        selectedTextColor = PrimaryIndigo,
                        unselectedIconColor = TextMutedDark,
                        unselectedTextColor = TextMutedDark,
                        indicatorColor = PrimaryIndigo.copy(alpha = 0.2f)
                    )
                )
                NavigationBarItem(
                    selected = currentTab == NavTab.SETTINGS,
                    onClick = { currentTab = NavTab.SETTINGS },
                    icon = { Icon(Icons.Default.Settings, contentDescription = "Settings") },
                    label = { Text("Settings") },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = PrimaryIndigo,
                        selectedTextColor = PrimaryIndigo,
                        unselectedIconColor = TextMutedDark,
                        unselectedTextColor = TextMutedDark,
                        indicatorColor = PrimaryIndigo.copy(alpha = 0.2f)
                    )
                )
            }
        }
    ) { innerPadding ->
        val modifier = Modifier.padding(innerPadding)
        when (currentTab) {
            NavTab.FEED -> NotesFeedScreen(
                repository = repository,
                onNavigateToFlashcards = { currentTab = NavTab.FLASHCARDS },
                modifier = modifier
            )
            NavTab.FLASHCARDS -> FlashcardsScreen(
                repository = repository,
                modifier = modifier
            )
            NavTab.DIGEST -> DigestScreen(
                repository = repository,
                modifier = modifier
            )
            NavTab.SETTINGS -> SettingsScreen(
                repository = repository,
                modifier = modifier
            )
        }
    }
}
