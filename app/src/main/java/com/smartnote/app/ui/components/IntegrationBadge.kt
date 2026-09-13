package com.smartnote.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.smartnote.app.ui.theme.*

@Composable
fun IntegrationBadge(
    label: String,
    icon: String,
    backgroundColor: Color,
    textColor: Color = Color.White,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier
            .background(backgroundColor, RoundedCornerShape(12.dp))
            .padding(horizontal = 8.dp, vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        Text(text = icon, fontSize = 11.sp)
        Text(
            text = label,
            color = textColor,
            fontSize = 11.sp,
            fontWeight = FontWeight.SemiBold
        )
    }
}

@Composable
fun DomainBadge(domain: String, modifier: Modifier = Modifier) {
    val (bgColor, label) = when (domain.uppercase()) {
        "TECH_EDUCATION" -> PrimaryIndigo.copy(alpha = 0.25f) to "Tech & Dev"
        "ENTERTAINMENT_REC" -> AccentSky.copy(alpha = 0.25f) to "Entertainment"
        "EVENT" -> AccentAmber.copy(alpha = 0.25f) to "Event / Date"
        "PROCESSING" -> AccentAmber.copy(alpha = 0.25f) to "Processing..."
        else -> TextMutedDark.copy(alpha = 0.25f) to "General"
    }

    Text(
        text = label,
        color = Color.White,
        fontSize = 11.sp,
        fontWeight = FontWeight.Medium,
        modifier = modifier
            .background(bgColor, RoundedCornerShape(8.dp))
            .padding(horizontal = 8.dp, vertical = 3.dp)
    )
}
