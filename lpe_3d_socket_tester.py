import math
import json
import time
from typing import Dict, Any, List, Tuple, Optional

class Vector3:
    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    def to_list(self) -> List[float]:
        return [round(self.x, 4), round(self.y, 4), round(self.z, 4)]

    def add(self, other: 'Vector3') -> 'Vector3':
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

class Quaternion:
    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0, w: float = 1.0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)
        self.w = float(w)

    def to_list(self) -> List[float]:
        return [round(self.x, 4), round(self.y, 4), round(self.z, 4), round(self.w, 4)]

class LPE3DSocketMappingEngine:
    """
    Live Persona Engine (LPE) 3D Asset Socket Mapping & Validation Engine.
    Handles 3D glTF/GLB cosmetic mesh binding to character skeleton sockets across
    KickBack WebGL stages and 9x9 Unity 6000 Netcode environments.
    """

    # Standardized Armature Socket Registry
    VALID_SOCKETS = {
        "head_socket": {"parent_bone": "Head", "default_offset": Vector3(0.0, 0.12, 0.05)},
        "chest_socket": {"parent_bone": "Spine2", "default_offset": Vector3(0.0, 0.0, 0.0)},
        "pelvis_socket": {"parent_bone": "Pelvis", "default_offset": Vector3(0.0, 0.0, 0.0)},
        "shoulder_socket_l": {"parent_bone": "LeftShoulder", "default_offset": Vector3(-0.18, 0.0, 0.0)},
        "shoulder_socket_r": {"parent_bone": "RightShoulder", "default_offset": Vector3(0.18, 0.0, 0.0)},
        "hand_socket_l": {"parent_bone": "LeftHand", "default_offset": Vector3(0.0, 0.02, 0.08)},
        "hand_socket_r": {"parent_bone": "RightHand", "default_offset": Vector3(0.0, 0.02, 0.08)},
        "body_skinned_mesh": {"parent_bone": "MasterArmature", "default_offset": Vector3(0.0, 0.0, 0.0)}
    }

    # Strict Performance & Memory Safeguards
    MAX_RIGID_POLYGONS = 3500
    MAX_SKINNED_POLYGONS = 12000
    MAX_TEXTURE_MEMORY_MB = 8.0

    def __init__(self):
        self.equipped_cosmetics: Dict[str, Dict[str, Any]] = {}

    def validate_asset_manifest(self, manifest: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validates 3D asset metadata against skeleton sockets and polygon/texture budgets.
        """
        config = manifest.get("attachmentConfig", {})
        target_socket = config.get("targetSocket")

        # 1. Socket Existence Check
        if target_socket not in self.VALID_SOCKETS:
            return False, f"Invalid target socket '{target_socket}'. Socket not found in LPE armature registry."

        # 2. Attachment Mode Check
        mode = config.get("attachmentMode")
        if mode not in ["RIGID_PARENT_CONSTRAINT", "SKINNED_MESH_WEIGHT_TRANSFER"]:
            return False, f"Unsupported attachment mode '{mode}'."

        # 3. Polygon Budget Verification
        limits = config.get("boundingBoxLimits", {})
        poly_count = limits.get("maxPolygonCount", 0)
        max_allowed_polys = self.MAX_SKINNED_POLYGONS if mode == "SKINNED_MESH_WEIGHT_TRANSFER" else self.MAX_RIGID_POLYGONS

        if poly_count > max_allowed_polys:
            return False, f"Polygon count ({poly_count}) exceeds limit ({max_allowed_polys}) for mode '{mode}'."

        # 4. Texture Memory Budget Verification
        tex_mem = limits.get("maxTextureMemoryMB", 0.0)
        if tex_mem > self.MAX_TEXTURE_MEMORY_MB:
            return False, f"Texture memory usage ({tex_mem} MB) exceeds limit ({self.MAX_TEXTURE_MEMORY_MB} MB)."

        return True, "Asset manifest validation successful."

    def compute_socket_world_transform(
        self,
        socket_id: str,
        local_offset: Vector3,
        local_rotation: Quaternion,
        local_scale: Vector3
    ) -> Dict[str, Any]:
        """
        Computes final world transform matrix offset for the socket attachment.
        """
        socket_info = self.VALID_SOCKETS[socket_id]
        base_offset = socket_info["default_offset"]

        final_pos = base_offset.add(local_offset)

        return {
            "targetSocket": socket_id,
            "parentBone": socket_info["parent_bone"],
            "worldPosition": final_pos.to_list(),
            "worldRotation": local_rotation.to_list(),
            "worldScale": local_scale.to_list()
        }

    def equip_3d_cosmetic(
        self,
        avatar_id: str,
        manifest: Dict[str, Any],
        custom_hex_colors: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Executes complete 3D socket attachment pipeline for an avatar instance.
        """
        valid, msg = self.validate_asset_manifest(manifest)
        if not valid:
            return {
                "success": False,
                "avatarId": avatar_id,
                "error": msg
            }

        config = manifest["attachmentConfig"]
        socket_id = config["targetSocket"]
        local_transform = config["localTransform"]

        pos_offset = Vector3(*local_transform["positionOffset"])
        rot_quat = Quaternion(*local_transform["rotationQuaternion"])
        scale_vec = Vector3(*local_transform["scaleVector"])

        transform = self.compute_socket_world_transform(socket_id, pos_offset, rot_quat, scale_vec)

        # Inject PBR Material Hex Overrides
        material_bindings = {}
        if custom_hex_colors and "dynamicColoring" in config:
            color_channels = config["dynamicColoring"].get("colorChannels", {})
            for channel_key, target_prop in color_channels.items():
                if channel_key in custom_hex_colors:
                    material_bindings[target_prop] = custom_hex_colors[channel_key]

        equipped_entry = {
            "assetId": manifest["assetId"],
            "assetName": manifest["assetName"],
            "contentHash": manifest["contentHash"],
            "attachmentMode": config["attachmentMode"],
            "transform": transform,
            "appliedColors": material_bindings,
            "equippedAt": int(time.time())
        }

        if avatar_id not in self.equipped_cosmetics:
            self.equipped_cosmetics[avatar_id] = {}

        self.equipped_cosmetics[avatar_id][socket_id] = equipped_entry

        return {
            "success": True,
            "avatarId": avatar_id,
            "socketId": socket_id,
            "attachmentResult": equipped_entry
        }

def run_lpe_3d_socket_test_suite():
    print("=================================================================")
    print("    LIVE PERSONA ENGINE (LPE): 3D SOCKET MAPPING TEST SUITE     ")
    print("=================================================================")

    engine = LPE3DSocketMappingEngine()
    avatar_id = "avatar_citizen_keith_001"

    # 1. Valid Rigid Head Socket Asset (Cyberpunk Neon Visor)
    visor_manifest = {
        "assetId": "asset_3d_cyber_visor_neon_09",
        "assetName": "Cyberpunk Neon Visor",
        "format": "glTF_2.0_GLB",
        "contentHash": "ipfs_QmX7b9f8a6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1a",
        "attachmentConfig": {
            "targetSocket": "head_socket",
            "attachmentMode": "RIGID_PARENT_CONSTRAINT",
            "localTransform": {
                "positionOffset": [0.0, 0.08, 0.04],
                "rotationQuaternion": [0.0, 0.0, 0.0, 1.0],
                "scaleVector": [1.0, 1.0, 1.0]
            },
            "dynamicColoring": {
                "colorChannels": {
                    "primary": "material_visor_frame.albedo",
                    "secondary": "material_visor_glass.emissive"
                }
            },
            "boundingBoxLimits": {
                "maxPolygonCount": 2400,
                "maxTextureMemoryMB": 4.5
            }
        }
    }

    # 2. Valid Skinned Chest Armor Asset
    armor_manifest = {
        "assetId": "asset_3d_tactical_chest_armor_01",
        "assetName": "Tactical Chest Armor",
        "format": "glTF_2.0_GLB",
        "contentHash": "ipfs_QmA1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
        "attachmentConfig": {
            "targetSocket": "chest_socket",
            "attachmentMode": "SKINNED_MESH_WEIGHT_TRANSFER",
            "localTransform": {
                "positionOffset": [0.0, 0.0, 0.0],
                "rotationQuaternion": [0.0, 0.0, 0.0, 1.0],
                "scaleVector": [1.0, 1.0, 1.0]
            },
            "dynamicColoring": {
                "colorChannels": {
                    "primary": "material_armor_plates.albedo"
                }
            },
            "boundingBoxLimits": {
                "maxPolygonCount": 8500,
                "maxTextureMemoryMB": 6.2
            }
        }
    }

    # 3. Invalid / Over-Budget Asset (Rejection Test)
    overbudget_manifest = {
        "assetId": "asset_3d_overbudget_wings_99",
        "assetName": "Unoptimized Ultra Wings",
        "format": "glTF_2.0_GLB",
        "contentHash": "ipfs_QmOverBudgetMeshHash123456789",
        "attachmentConfig": {
            "targetSocket": "chest_socket",
            "attachmentMode": "RIGID_PARENT_CONSTRAINT",
            "localTransform": {
                "positionOffset": [0.0, 0.0, -0.1],
                "rotationQuaternion": [0.0, 0.0, 0.0, 1.0],
                "scaleVector": [1.0, 1.0, 1.0]
            },
            "boundingBoxLimits": {
                "maxPolygonCount": 25000,  # Exceeds 3,500 limit for rigid
                "maxTextureMemoryMB": 16.0  # Exceeds 8.0 MB limit
            }
        }
    }

    # Execute Test 1: Equip Head Visor with Custom Hex Colors
    colors_visor = {"primary": "#00FFCC", "secondary": "#FF0077"}
    res1 = engine.equip_3d_cosmetic(avatar_id, visor_manifest, colors_visor)
    assert res1["success"] is True, f"Test 1 failed: {res1.get('error')}"
    print(f"✅ TEST 1 (Head Socket Attachment): PASS [Equipped: '{res1['attachmentResult']['assetName']}']")
    print(f"   World Position: {res1['attachmentResult']['transform']['worldPosition']}")
    print(f"   PBR Colors Applied: {res1['attachmentResult']['appliedColors']}")

    # Execute Test 2: Equip Skinned Chest Armor
    colors_armor = {"primary": "#1A1A1A"}
    res2 = engine.equip_3d_cosmetic(avatar_id, armor_manifest, colors_armor)
    assert res2["success"] is True, f"Test 2 failed: {res2.get('error')}"
    print(f"✅ TEST 2 (Skinned Chest Attachment): PASS [Equipped: '{res2['attachmentResult']['assetName']}']")
    print(f"   Attachment Mode: {res2['attachmentResult']['attachmentMode']}")

    # Execute Test 3: Over-Budget Asset Rejection
    res3 = engine.equip_3d_cosmetic(avatar_id, overbudget_manifest)
    assert res3["success"] is False, "Test 3 failed: Overbudget asset was not rejected!"
    print(f"✅ TEST 3 (Over-Budget Asset Rejection): PASS [{res3['error']}]")

    print("\n=================================================================")
    print("FINAL LPE 3D SOCKET MAPPING VERIFICATION STATUS: PASS")
    print("=================================================================")

if __name__ == "__main__":
    run_lpe_3d_socket_test_suite()
