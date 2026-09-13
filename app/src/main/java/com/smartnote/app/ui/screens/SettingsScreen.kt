package com.smartnote.app.ui.screens

import android.widget.Toast
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
import com.smartnote.app.ui.theme.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@Composable
fun SettingsScreen(
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var baseUrl by remember { mutableStateOf(RetrofitClient.getBaseUrl(context)) }
    var connectionStatus by remember { mutableStateOf<String?>(null) }
    var isChecking by remember { mutableStateOf(false) }

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(BackgroundDark)
            .padding(16.dp)
            .verticalScroll(rememberScrollState())
    ) {
        Spacer(modifier = Modifier.height(16.dp))

        Text(
            text = "Pipeline Settings",
            color = TextPrimaryDark,
            fontSize = 20.sp,
            fontWeight = FontWeight.Bold
        )
        Text(
            text = "Configure your backend endpoint and device optimization",
            color = TextMutedDark,
            fontSize = 12.sp
        )

        Spacer(modifier = Modifier.height(20.dp))

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
                    text = "Many Android manufacturers (Samsung, Xiaomi, OnePlus, Motorola, Vivo) apply strict background task limits to conserve battery. SmartNote utilizes AndroidX WorkManager with exponential backoff constraints and network type guarantees. When you share a Reel or Short, the task is persisted to system SQLite and processed reliably in the background without UI blocking.",
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
                Text("• ⭐ GitHub: Stars owner/repo via REST API & Personal Access Token.", color = TextSecondaryDark, fontSize = 12.sp)
                Text("• 🎵 Spotify: Appends discovered songs to your Spotify playlist.", color = TextSecondaryDark, fontSize = 12.sp)
                Text("• 🎬 TMDB: Adds movies/series to your TMDB watchlist.", color = TextSecondaryDark, fontSize = 12.sp)
                Text("• 📝 Notion: Appends structured notes and flashcards to Notion.", color = TextSecondaryDark, fontSize = 12.sp)
                Text("• 📅 Calendar: Generates native .ics files for one-tap imports.", color = TextSecondaryDark, fontSize = 12.sp)
            }
        }
    }
}
