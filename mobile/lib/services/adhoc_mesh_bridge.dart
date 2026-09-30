import 'package:flutter/services.dart'; 
import 'package:sqflite/sqflite.dart'; 
//import 'dart:convert'; 
class AdHocMeshBridge { static const MethodChannel platform = MethodChannel('com.kickback/mesh_radio'); 
final Database db; AdHocMeshBridge({required this.db});} /// Initializes hardware radio discovery and listens for raw mesh packets Future