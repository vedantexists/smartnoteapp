package com.smartnote.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.smartnote.app.data.repository.NoteRepository
import com.smartnote.app.ui.components.FlashcardFlipView
import com.smartnote.app.ui.theme.*
import kotlinx.coroutines.launch

@Composable
fun FlashcardsScreen(
    repository: NoteRepository,
    modifier: Modifier = Modifier
) {
    val scope = rememberCoroutineScope()
    val flashcards by repository.allFlashcards.collectAsState(initial = emptyList())

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
                    text = "Active Recall",
                    color = TextPrimaryDark,
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = "Tap to flip • Practice spaced repetition",
                    color = TextMutedDark,
                    fontSize = 12.sp
                )
            }

            Surface(
                color = SurfaceDark,
                shape = MaterialTheme.shapes.medium
            ) {
                Text(
                    text = "${flashcards.size} Cards",
                    color = AccentEmerald,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp)
                )
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        if (flashcards.isEmpty()) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(32.dp),
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text("🧠", fontSize = 48.sp)
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        text = "No flashcards yet",
                        color = TextPrimaryDark,
                        fontWeight = FontWeight.Bold,
                        fontSize = 18.sp
                    )
                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        text = "When you share educational tech reels or coding tutorials, Gemini automatically generates active recall test cards here!",
                        color = TextMutedDark,
                        fontSize = 13.sp,
                        textAlign = TextAlign.Center
                    )
                }
            }
        } else {
            LazyColumn(
                verticalArrangement = Arrangement.spacedBy(16.dp),
                contentPadding = PaddingValues(bottom = 32.dp)
            ) {
                items(flashcards, key = { it.id }) { card ->
                    FlashcardFlipView(
                        flashcard = card,
                        onReviewed = { cardId ->
                            scope.launch {
                                repository.recordFlashcardReview(cardId)
                            }
                        }
                    )
                }
            }
        }
    }
}
