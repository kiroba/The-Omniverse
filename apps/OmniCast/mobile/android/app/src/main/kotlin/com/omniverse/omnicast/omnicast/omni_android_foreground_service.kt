package com.omniverse.omnicast.omnicast

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat

class OmniAndroidForegroundService : Service() {

    companion object {
        const val CHANNEL_ID = "omni_p2p_daemon_channel"
        const val NOTIFICATION_ID = 91001

        fun startService(context: Context) {
            val startIntent = Intent(context, OmniAndroidForegroundService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(startIntent)
            } else {
                context.startService(startIntent)
            }
        }

        fun stopService(context: Context) {
            val stopIntent = Intent(context, OmniAndroidForegroundService::class.java)
            context.stopService(stopIntent)
        }
    }

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val notification: Notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("OmniCast P2P Mesh Active")
            .setContentText("Listening on ports :5000 and :5005 for decentralized P2P signals")
            .setSmallIcon(android.R.drawable.ic_menu_compass)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setOngoing(true)
            .build()

        startForeground(NOTIFICATION_ID, notification)

        // START_STICKY ensures OS restarts the daemon service if killed under memory pressure
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? {
        return null
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "OmniCast P2P Mesh Service",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Keeps P2P network sockets active when screen is off"
            }
            val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            manager.createNotificationChannel(channel)
        }
    }
}
