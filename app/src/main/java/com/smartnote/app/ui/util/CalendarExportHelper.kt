package com.smartnote.app.ui.util

import android.content.Context
import android.content.Intent
import android.widget.Toast
import androidx.core.content.FileProvider
import java.io.File
import java.io.FileOutputStream

object CalendarExportHelper {

    fun exportAndOpenCalendar(context: Context, icsContent: String, eventTitle: String = "event") {
        try {
            val eventsDir = File(context.cacheDir, "events").apply {
                if (!exists()) mkdirs()
            }

            val sanitizedTitle = eventTitle.replace("[^a-zA-Z0-9]".toRegex(), "_").take(20)
            val file = File(eventsDir, "${sanitizedTitle}_${System.currentTimeMillis()}.ics")

            FileOutputStream(file).use { out ->
                out.write(icsContent.toByteArray(Charsets.UTF_8))
            }

            val contentUri = FileProvider.getUriForFile(
                context,
                "${context.packageName}.fileprovider",
                file
            )

            val intent = Intent(Intent.ACTION_VIEW).apply {
                setDataAndType(contentUri, "text/calendar")
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }

            val chooser = Intent.CreateChooser(intent, "Import into Calendar").apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(chooser)

        } catch (e: Exception) {
            Toast.makeText(context, "Could not open calendar: ${e.localizedMessage}", Toast.LENGTH_SHORT).show()
        }
    }
}
