package com.smartnote.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.smartnote.app.data.remote.model.WeeklyDigestResponseDto
import com.smartnote.app.data.repository.NoteRepository
import com.smartnote.app.ui.theme.*
import kotlinx.coroutines.launch

@Composable
fun DigestScreen(
    repository: NoteRepository,
    modifier: Modifier = Modifier
) {
    val scope = rememberCoroutineScope()
    var digest by remember { mutableStateOf<WeeklyDigestResponseDto?>(null) }
    var isLoading by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    fun loadDigest(force: Boolean = false) {
        isLoading = true
        errorMessage = null
        scope.launch {
            val result = repository.fetchWeeklyDigest(forceRefresh = force)
            isLoading = false
            result.onSuccess { data ->
                digest = data
            }.onFailure { err ->
                errorMessage = err.localizedMessage ?: "Failed to load weekly digest"
            }
        }
    }

    LaunchedEffect(Unit) {
        loadDigest(force = false)
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(BackgroundDark)
            .padding(horizontal = 16.dp)
    ) {
        Spacer(modifier = Modifier.height(16.dp))

        // Header
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(
                    text = "Sunday Weekly Digest",
                    color = TextPrimaryDark,
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = "Automated AI synthesis every Sunday at 00:00 UTC",
                    color = TextMutedDark,
                    fontSize = 11.sp
                )
            }

            IconButton(onClick = { loadDigest(force = true) }) {
                Icon(Icons.Default.Refresh, contentDescription = "Refresh", tint = PrimaryIndigo)
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        if (isLoading) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = PrimaryIndigo)
            }
        } else if (errorMessage != null && digest == null) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text("⚠️", fontSize = 40.sp)
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(text = errorMessage!!, color = AccentRose, fontSize = 13.sp)
                    Spacer(modifier = Modifier.height(12.dp))
                    Button(onClick = { loadDigest(force = true) }) {
                        Text("Try Again")
                    }
                }
            }
        } else if (digest != null) {
            val d = digest!!
            LazyColumn(
                verticalArrangement = Arrangement.spacedBy(14.dp),
                contentPadding = PaddingValues(bottom = 32.dp)
            ) {
                // Summary Card
                item {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(16.dp),
                        colors = CardDefaults.cardColors(containerColor = SurfaceDark),
                        border = CardDefaults.outlinedCardBorder().copy(brush = androidx.compose.ui.graphics.SolidColor(CardBorderDark))
                    ) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Text(
                                    text = "📊 Overview",
                                    color = PrimaryIndigo,
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.Bold
                                )
                                Text(
                                    text = "${d.totalNotesProcessed} Notes Processed",
                                    color = AccentEmerald,
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.SemiBold
                                )
                            }
                            Spacer(modifier = Modifier.height(8.dp))
                            Text(
                                text = d.digestSummary,
                                color = TextPrimaryDark,
                                fontSize = 14.sp,
                                lineHeight = 20.sp
                            )
                        }
                    }
                }

                // Top Themes
                if (d.topTopics.isNotEmpty()) {
                    item {
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(16.dp),
                            colors = CardDefaults.cardColors(containerColor = SurfaceDark),
                            border = CardDefaults.outlinedCardBorder().copy(brush = androidx.compose.ui.graphics.SolidColor(CardBorderDark))
                        ) {
                            Column(modifier = Modifier.padding(16.dp)) {
                                Text(
                                    text = "🔥 Key Themes This Week",
                                    color = AccentAmber,
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.Bold
                                )
                                Spacer(modifier = Modifier.height(8.dp))
                                d.topTopics.forEach { topic ->
                                    Text(
                                        text = "• $topic",
                                        color = TextSecondaryDark,
                                        fontSize = 13.sp,
                                        modifier = Modifier.padding(vertical = 2.dp)
                                    )
                                }
                            }
                        }
                    }
                }

                // Notable Tools
                if (d.notableTools.isNotEmpty()) {
                    item {
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(16.dp),
                            colors = CardDefaults.cardColors(containerColor = SurfaceDark),
                            border = CardDefaults.outlinedCardBorder().copy(brush = androidx.compose.ui.graphics.SolidColor(CardBorderDark))
                        ) {
                            Column(modifier = Modifier.padding(16.dp)) {
                                Text(
                                    text = "🛠️ Top Discovered Tools",
                                    color = AccentSky,
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.Bold
                                )
                                Spacer(modifier = Modifier.height(8.dp))
                                d.notableTools.forEach { tool ->
                                    Column(modifier = Modifier.padding(vertical = 4.dp)) {
                                        Text(tool.name, color = TextPrimaryDark, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                                        Text(tool.purpose, color = TextMutedDark, fontSize = 11.sp)
                                    }
                                }
                            }
                        }
                    }
                }

                // Weekly Spaced Repetition Highlights
                if (d.highlightFlashcards.isNotEmpty()) {
                    item {
                        Text(
                            text = "🧠 Weekly Spaced Repetition Highlights",
                            color = TextPrimaryDark,
                            fontSize = 15.sp,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(top = 8.dp)
                        )
                    }
                    items(d.highlightFlashcards) { fc ->
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(14.dp),
                            colors = CardDefaults.cardColors(containerColor = SurfaceDark),
                            border = CardDefaults.outlinedCardBorder().copy(brush = androidx.compose.ui.graphics.SolidColor(CardBorderDark))
                        ) {
                            Column(modifier = Modifier.padding(14.dp)) {
                                Text("Q: ${fc.question}", color = PrimaryIndigo, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                                Spacer(modifier = Modifier.height(4.dp))
                                Text("A: ${fc.answer}", color = TextSecondaryDark, fontSize = 12.sp)
                                if (!fc.keyTakeaway.isNullOrBlank()) {
                                    Spacer(modifier = Modifier.height(4.dp))
                                    Text("Takeaway: ${fc.keyTakeaway}", color = AccentAmber, fontSize = 11.sp)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
