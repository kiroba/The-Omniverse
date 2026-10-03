package com.kickback import io.flutter.embedding.android.FlutterActivity 
class MainActivity: 
        FlutterActivity() { }


package com.kickback import io.flutter.embedding.android.FlutterActivity import io.flutter.embedding.engine.FlutterEngine import io.flutter.plugin.common.MethodChannel import android.net.wifi.aware.WifiAwareManager import android.content.Context 

class 
MainActivity: FlutterActivity() 
{ private val CHANNEL = "com.kickback/mesh\_radio" override fun configureFlutterEngine(flutterEngine: FlutterEngine) { super.configureFlutterEngine(flutterEngine) MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL).setMethodCallHandler { call, result -&gt; when (call.method) { "startLocalMeshScan" -&gt; { val wifiAwareManager = getSystemService(Context.WIFI\_AWARE\_SERVICE) as? WifiAwareManager if (wifiAwareManager?.isAvailable == true) { // Native Wi-Fi Aware discovery active result.success(mapOf("status" to "ACTIVE", "transport" to "WIFI\_AWARE")) } else { // Fallback to Bluetooth LE discovery result.success(mapOf("status" to "FALLBACK", "transport" to "BLE")) } } else -&gt; result.notImplemented() } } } }