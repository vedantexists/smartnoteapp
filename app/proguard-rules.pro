# ProGuard configuration for SmartNote Android app
-keepattributes *Annotation*
-keepclassmembers class * {
    @androidx.room.* <methods>;
}
-keep class com.smartnote.app.data.remote.model.** { *; }
