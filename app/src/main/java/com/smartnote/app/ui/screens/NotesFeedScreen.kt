package com.smartnote.app.ui.screens

import android.content.Intent
import android.net.Uri
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material.icons.filled.OpenInBrowser
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import com.smartnote.app.data.local.NoteWithDetails
import com.smartnote.app.data.remote.model.SearchItemDto
import com.smartnote.app.data.repository.NoteRepository
import com.smartnote.app.ui.components.DomainBadge
import com.smartnote.app.ui.components.IntegrationBadge
import com.smartnote.app.ui.components.SemanticSearchBar
import com.smartnote.app.ui.theme.*
import com.smartnote.app.ui.util.CalendarExportHelper
import kotlinx.coroutines.launch

@Composable
fun NotesFeedScreen(
    repository: NoteRepository,
    onNavigateToFlashcards: () -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val allNotes by repository.activeNotes.collectAsState(initial = emptyList())

    var searchQuery by remember { mutableStateOf("") }
    var searchResults by remember { mutableStateOf<List<SearchItemDto>?>(null) }
    var isSearching by remember { mutableStateOf(false) }
    var selectedCategory by remember { mutableStateOf("ALL") }

    val categories = listOf("ALL", "TECH_EDUCATION", "ENTERTAINMENT_REC", "EVENT", "OTHER")

    // Filter notes based on selected category or search
    val displayedNotes = remember(allNotes, selectedCategory, searchResults) {
        if (searchResults != null) {
            // Display search results matched from DB
            val ids = searchResults!!.map { it.note.id }.toSet()
            allNotes.filter { it.note.id in ids }
        } else if (selectedCategory == "ALL") {
            allNotes
        } else {
            allNotes.filter { it.note.domain.equals(selectedCategory, ignoreCase = true) }
        }
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(BackgroundDark)
            .padding(horizontal = 16.dp)
    ) {
        Spacer(modifier = Modifier.height(16.dp))

        // Search Bar
        SemanticSearchBar(
            query = searchQuery,
            onQueryChange = {
                searchQuery = it
                if (it.isBlank()) {
                    searchResults = null
                }
            },
            onSearch = { query ->
                if (query.isNotBlank()) {
                    isSearching = true
                    scope.launch {
                        val res = repository.searchRemote(query)
                        isSearching = false
                        res.onSuccess { data ->
                            searchResults = data.results
                        }
                    }
                } else {
                    searchResults = null
                }
            }
        )

        Spacer(modifier = Modifier.height(12.dp))

        // Category Filter Chips
        LazyRow(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            items(categories) { cat ->
                val isSelected = selectedCategory == cat && searchResults == null
                val label = when (cat) {
                    "ALL" -> "All Notes"
                    "TECH_EDUCATION" -> "💻 Tech"
                    "ENTERTAINMENT_REC" -> "🎬 Media"
                    "EVENT" -> "📅 Events"
                    else -> "📌 General"
                }

                FilterChip(
                    selected = isSelected,
                    onClick = {
                        selectedCategory = cat
                        searchResults = null
                    },
                    label = { Text(label, fontSize = 12.sp) },
                    colors = FilterChipDefaults.filterChipColors(
                        selectedContainerColor = PrimaryIndigo,
                        selectedLabelColor = Color.White,
                        containerColor = SurfaceDark,
                        labelColor = TextSecondaryDark
                    ),
                    border = FilterChipDefaults.filterChipBorder(
                        enabled = true,
                        selected = isSelected,
                        borderColor = CardBorderDark,
                        selectedBorderColor = PrimaryIndigo
                    )
                )
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        if (isSearching) {
            Box(modifier = Modifier.fillMaxWidth().padding(16.dp), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = PrimaryIndigo, modifier = Modifier.size(28.dp))
            }
        }

        if (displayedNotes.isEmpty()) {
            // Empty State
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(32.dp),
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text("📱", fontSize = 48.sp)
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        text = "No notes found",
                        color = TextPrimaryDark,
                        fontWeight = FontWeight.Bold,
                        fontSize = 18.sp
                    )
                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        text = "Share any Instagram Reel or YouTube Short using Android Share to automatically extract notes, repos, and flashcards!",
                        color = TextMutedDark,
                        fontSize = 13.sp,
                        textAlign = androidx.compose.ui.text.style.TextAlign.Center
                    )
                }
            }
        } else {
            LazyColumn(
                verticalArrangement = Arrangement.spacedBy(14.dp),
                contentPadding = PaddingValues(bottom = 32.dp)
            ) {
                items(displayedNotes, key = { it.note.id }) { item ->
                    NoteCard(item = item)
                }
            }
        }
    }
}

@Composable
fun NoteCard(item: NoteWithDetails) {
    val context = LocalContext.current
    var isExpanded by remember { mutableStateOf(false) }

    val gson = remember { Gson() }
    val stringListType = object : TypeToken<List<String>>() {}.type

    val starredRepos: List<String> = remember(item.note.githubStarredJson) {
        try { gson.fromJson(item.note.githubStarredJson, stringListType) ?: emptyList() } catch (e: Exception) { emptyList() }
    }
    val spotifyTracks: List<String> = remember(item.note.spotifyAddedJson) {
        try { gson.fromJson(item.note.spotifyAddedJson, stringListType) ?: emptyList() } catch (e: Exception) { emptyList() }
    }
    val tmdbItems: List<String> = remember(item.note.tmdbAddedJson) {
        try { gson.fromJson(item.note.tmdbAddedJson, stringListType) ?: emptyList() } catch (e: Exception) { emptyList() }
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = SurfaceDark),
        border = CardDefaults.outlinedCardBorder().copy(brush = androidx.compose.ui.graphics.SolidColor(CardBorderDark))
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            // Header: Category and Status
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                DomainBadge(domain = item.note.domain)

                if (item.note.status == "PROCESSING") {
                    Text("⏳ Processing...", color = AccentAmber, fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
                } else if (item.note.status == "MERGED") {
                    Text("⚡ Merged & Consolidated", color = AccentEmerald, fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
                }
            }

            Spacer(modifier = Modifier.height(10.dp))

            // Title
            Text(
                text = item.note.title,
                color = TextPrimaryDark,
                fontSize = 17.sp,
                fontWeight = FontWeight.Bold
            )

            Spacer(modifier = Modifier.height(6.dp))

            // Summary
            Text(
                text = item.note.summary,
                color = TextSecondaryDark,
                fontSize = 13.sp,
                lineHeight = 18.sp
            )

            // Integration Badges Row
            Spacer(modifier = Modifier.height(12.dp))
            Row(
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                if (starredRepos.isNotEmpty()) {
                    IntegrationBadge(
                        label = "Starred (${starredRepos.size})",
                        icon = "⭐",
                        backgroundColor = GitHubBadgeColor
                    )
                }
                if (spotifyTracks.isNotEmpty()) {
                    IntegrationBadge(
                        label = "Spotify (${spotifyTracks.size})",
                        icon = "🎵",
                        backgroundColor = SpotifyBadgeColor
                    )
                }
                if (tmdbItems.isNotEmpty()) {
                    IntegrationBadge(
                        label = "TMDB (${tmdbItems.size})",
                        icon = "🎬",
                        backgroundColor = TmdbBadgeColor
                    )
                }
                if (item.note.notionSynced) {
                    IntegrationBadge(
                        label = "Notion",
                        icon = "📝",
                        backgroundColor = NotionBadgeColor
                    )
                }
            }

            // Expandable Detailed Content
            AnimatedVisibility(visible = isExpanded) {
                Column(modifier = Modifier.padding(top = 14.dp)) {
                    Divider(color = CardBorderDark, thickness = 1.dp)
                    Spacer(modifier = Modifier.height(10.dp))

                    if (item.note.detailedNotes.isNotBlank()) {
                        Text("Detailed Notes", color = TextPrimaryDark, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = item.note.detailedNotes,
                            color = TextSecondaryDark,
                            fontSize = 12.sp,
                            lineHeight = 17.sp
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                    }

                    // Web Resources
                    if (item.linkItems.isNotEmpty()) {
                        Text("Discovered Tools & Links", color = PrimaryIndigo, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                        Spacer(modifier = Modifier.height(6.dp))
                        item.linkItems.forEach { link ->
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(vertical = 4.dp)
                                    .clickable {
                                        try {
                                            context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(link.url)))
                                        } catch (_: Exception) {}
                                    },
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Column(modifier = Modifier.weight(1f)) {
                                    Text(link.name, color = TextPrimaryDark, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                                    Text(link.purpose, color = TextMutedDark, fontSize = 11.sp)
                                }
                                Icon(Icons.Default.OpenInBrowser, contentDescription = "Open", tint = PrimaryIndigo, modifier = Modifier.size(16.dp))
                            }
                        }
                        Spacer(modifier = Modifier.height(12.dp))
                    }

                    // Calendar Event Action
                    if (!item.note.eventIcs.isNullOrBlank()) {
                        Button(
                            onClick = {
                                CalendarExportHelper.exportAndOpenCalendar(context, item.note.eventIcs, item.note.title)
                            },
                            colors = ButtonDefaults.buttonColors(containerColor = AccentAmber),
                            shape = RoundedCornerShape(10.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Icon(Icons.Default.DateRange, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(8.dp))
                            Text("📅 Add Event to Native Calendar", color = Color.Black, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                        }
                        Spacer(modifier = Modifier.height(8.dp))
                    }

                    // Source link
                    if (item.note.sourceUrl.isNotBlank()) {
                        Text(
                            text = "Source: ${item.note.sourceUrl}",
                            color = TextMutedDark,
                            fontSize = 10.sp,
                            modifier = Modifier.clickable {
                                try {
                                    context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(item.note.sourceUrl)))
                                } catch (_: Exception) {}
                            }
                        )
                    }
                }
            }

            // Expand/Collapse Toggle Button
            Spacer(modifier = Modifier.height(8.dp))
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { isExpanded = !isExpanded }
                    .padding(vertical = 4.dp),
                horizontalArrangement = Arrangement.Center,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = if (isExpanded) "Show Less" else "View Details & Links",
                    color = PrimaryIndigo,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold
                )
                Icon(
                    imageVector = if (isExpanded) Icons.Default.KeyboardArrowUp else Icons.Default.KeyboardArrowDown,
                    contentDescription = null,
                    tint = PrimaryIndigo,
                    modifier = Modifier.size(18.dp)
                )
            }
        }
    }
}
