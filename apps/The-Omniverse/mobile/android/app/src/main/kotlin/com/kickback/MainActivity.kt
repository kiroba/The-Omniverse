package com.kickback

import android.content.Context
import android.net.wifi.aware.WifiAwareManager
import android.os.Build
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private val channelName = "com.kickback/mesh_radio"

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, channelName)
            .setMethodCallHandler { call, result ->
                if (call.method != "startLocalMeshScan") {
                    result.notImplemented()
                    return@setMethodCallHandler
                }

                val wifiAwareManager =
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        getSystemService(Context.WIFI_AWARE_SERVICE) as? WifiAwareManager
                    } else {
                        null
                    }

                val available = wifiAwareManager?.isAvailable == true
                result.success(
                    mapOf(
                        "status" to if (available) "ACTIVE" else "FALLBACK",
                        "transport" to if (available) "WIFI_AWARE" else "BLE",
                    ),
                )
            }
    }
}
