# ============================================================================
# OMNIVERSE & PHASER 2D: MULTI-INDUSTRY CREATOR STARTER TEMPLATES & TUTORIALS
# Protocol Tag: [FUNDAMENTAL_FEATURE_TAG: LOCALSEND_PHASER_STUDIO_V1]
# ============================================================================

import json
from pathlib import Path
from typing import Dict, Any

TEMPLATES: Dict[str, Dict[str, Any]] = {
    "ARCADE_GAME": {
        "template_id": "tpl_arcade_cyber_runner_2d",
        "title": "Cyber Runner 2D: Arcade Starter Template",
        "industry": "Gaming & Esports",
        "description": "Fluid 2D platformer template with collision maps, sprite animations, and P2P score leaderboard broadcasting.",
        "manifest": {
            "schema_version": "1.0.0",
            "mod_id": "omnimod.templates.cyber_runner_2d",
            "version": "1.0.0",
            "title": "Cyber Runner 2D",
            "description": "2D neon platformer with local P2P score synchronization.",
            "category": "arcade_game",
            "author": {
                "handle": "@omniverse.official",
                "pubkey_ed25519": "0x0000000000000000000000000000000000000000000000000000000000000001",
                "attestation_badge": "ENTERPRISE_STUDIO"
            },
            "engine_target": {
                "framework": "phaser_3_canvas",
                "min_framework_version": "3.80.0",
                "entrypoint": "src/game_logic.js",
                "sandbox_permissions": [
                    "CANVAS_RENDER_2D",
                    "AUDIO_PLAYBACK",
                    "LOCAL_KEYBOARD_TOUCH_INPUT",
                    "OMNI_P2P_SCORE_BROADCAST"
                ]
            },
            "assets": {
                "spritesheets": [
                    {"key": "player_run", "file_path": "assets/sprites/runner.png", "frame_width": 64, "frame_height": 64}
                ],
                "tilemaps": [
                    {"key": "stage_01", "file_path": "assets/maps/level1.json", "format": "TILED_JSON"}
                ],
                "audio_banks": [
                    {"key": "sfx_jump", "file_path": "assets/audio/jump.ogg"}
                ]
            },
            "kickback_integration": {
                "max_players": 4,
                "omnicredits_reward_rate": 1.5,
                "telemetry_events": ["LEVEL_COMPLETE", "HIGH_SCORE"]
            }
        },
        "phaser_code_snippet": """
// Cyber Runner 2D - Boilerplate Scene
class CyberRunnerScene extends Phaser.Scene {
    constructor() { super({ key: 'CyberRunnerScene' }); }
    preload() {
        this.load.spritesheet('player_run', 'assets/sprites/runner.png', { frameWidth: 64, frameHeight: 64 });
        this.load.tilemapTiledJSON('stage_01', 'assets/maps/level1.json');
        this.load.audio('sfx_jump', 'assets/audio/jump.ogg');
    }
    create() {
        const map = this.make.tilemap({ key: 'stage_01' });
        const tileset = map.addTilesetImage('neon_tiles', 'tileset_img');
        const layer = map.createLayer('World', tileset, 0, 0);
        layer.setCollisionByProperty({ collides: true });
        
        this.player = this.physics.add.sprite(100, 450, 'player_run');
        this.physics.add.collider(this.player, layer);
        this.cursors = this.input.keyboard.createCursorKeys();
    }
    update() {
        if (this.cursors.left.isDown) { this.player.setVelocityX(-200); }
        else if (this.cursors.right.isDown) { this.player.setVelocityX(200); }
        else { this.player.setVelocityX(0); }
        if (this.cursors.up.isDown && this.player.body.blocked.down) {
            this.player.setVelocityY(-400);
        }
    }
}
"""
    },
    "EDUCATOR_PASS": {
        "template_id": "tpl_educator_quantum_pass",
        "title": "Quantum Computing Educator Pass & Quiz Vault",
        "industry": "EdTech & Professional Certification",
        "description": "Interactive learning pass with embedded quiz modules, completion credentials, and OmniCredit rewards.",
        "manifest": {
            "schema_version": "1.0.0",
            "mod_id": "omnimod.templates.quantum_educator_pass",
            "version": "1.0.0",
            "title": "Quantum Physics Educator Pass",
            "description": "Interactive lesson modules and verifiable local completion certificates.",
            "category": "puzzle",
            "author": {
                "handle": "@quantum.academy",
                "pubkey_ed25519": "0x0000000000000000000000000000000000000000000000000000000000000002",
                "attestation_badge": "ENTERPRISE_STUDIO"
            },
            "engine_target": {
                "framework": "phaser_3_canvas",
                "min_framework_version": "3.80.0",
                "entrypoint": "src/educator_logic.js",
                "sandbox_permissions": [
                    "CANVAS_RENDER_2D",
                    "LOCAL_KEYBOARD_TOUCH_INPUT",
                    "OMNI_P2P_SCORE_BROADCAST"
                ]
            },
            "assets": {
                "spritesheets": [
                    {"key": "quiz_cards", "file_path": "assets/ui/cards.png", "frame_width": 200, "frame_height": 300}
                ],
                "tilemaps": [],
                "audio_banks": [
                    {"key": "sfx_correct", "file_path": "assets/audio/correct.ogg"}
                ]
            },
            "kickback_integration": {
                "max_players": 1,
                "omnicredits_reward_rate": 5.0,
                "telemetry_events": ["QUIZ_PASSED", "PASS_ISSUED"]
            }
        },
        "phaser_code_snippet": """
// Educator Pass - Interactive Card Quiz
class EducatorQuizScene extends Phaser.Scene {
    constructor() { super({ key: 'EducatorQuizScene' }); }
    create() {
        this.add.text(100, 50, 'Quantum Computing Module 1: Qubits', { fontSize: '24px', fill: '#00FFCC' });
        this.card = this.add.image(400, 300, 'quiz_cards', 0).setInteractive();
        this.card.on('pointerdown', () => {
            this.sound.play('sfx_correct');
            window.OmniIPC.sendEvent('QUIZ_PASSED', { score: 100, mod_id: 'quantum_pass' });
        });
    }
}
"""
    },
    "LPE_COSMETIC_PACK": {
        "template_id": "tpl_lpe_neon_aura_pack",
        "title": "LPE Cyberpunk Neon Aura 2D Layer Pack",
        "industry": "Digital Fashion & Avatar Cosmetics",
        "description": "Modular 2D avatar clothing layers and sprite attachments for the Live Persona Engine.",
        "manifest": {
            "schema_version": "1.0.0",
            "mod_id": "omnimod.templates.neon_aura_lpe_pack",
            "version": "1.0.0",
            "title": "Neon Aura LPE Cosmetic Pack",
            "description": "Modular 2D sprite clothing layers for Live Persona Engine avatars.",
            "category": "cosmetic_skin",
            "author": {
                "handle": "@cyber.style",
                "pubkey_ed25519": "0x0000000000000000000000000000000000000000000000000000000000000003",
                "attestation_badge": "HUMAN_VERIFIED_CREATOR"
            },
            "engine_target": {
                "framework": "phaser_3_canvas",
                "min_framework_version": "3.80.0",
                "entrypoint": "src/cosmetic_viewer.js",
                "sandbox_permissions": ["CANVAS_RENDER_2D"]
            },
            "assets": {
                "spritesheets": [
                    {"key": "aura_layer", "file_path": "assets/cosmetics/aura.png", "frame_width": 128, "frame_height": 128}
                ],
                "tilemaps": [],
                "audio_banks": []
            },
            "kickback_integration": {
                "max_players": 1,
                "omnicredits_reward_rate": 0.0,
                "telemetry_events": ["COSMETIC_EQUIPPED"]
            }
        },
        "phaser_code_snippet": """
// LPE Cosmetic Layer Attachment Preview
class CosmeticPreviewScene extends Phaser.Scene {
    create() {
        const aura = this.add.sprite(400, 300, 'aura_layer');
        this.tweens.add({
            targets: aura,
            alpha: { from: 0.4, to: 1.0 },
            duration: 800,
            yoyo: true,
            repeat: -1
        });
    }
}
"""
    },
    "PUZZLE_VAULT": {
        "template_id": "tpl_puzzle_9x9_cube_escape",
        "title": "9x9 Procedural Cube Escape Tilemap",
        "industry": "Procedural Gaming & Logic Puzzles",
        "description": "Procedurally generated 2D maze-escape puzzle grid with trap rooms and keycard scavenging.",
        "manifest": {
            "schema_version": "1.0.0",
            "mod_id": "omnimod.templates.cube_escape_9x9",
            "version": "1.0.0",
            "title": "9x9 Procedural Cube Escape",
            "description": "Procedural maze-escape tilemap with local P2P room sync.",
            "category": "puzzle",
            "author": {
                "handle": "@hactik.games",
                "pubkey_ed25519": "0x0000000000000000000000000000000000000000000000000000000000000004",
                "attestation_badge": "ENTERPRISE_STUDIO"
            },
            "engine_target": {
                "framework": "phaser_3_canvas",
                "min_framework_version": "3.80.0",
                "entrypoint": "src/cube_logic.js",
                "sandbox_permissions": [
                    "CANVAS_RENDER_2D",
                    "AUDIO_PLAYBACK",
                    "LOCAL_KEYBOARD_TOUCH_INPUT",
                    "OMNI_P2P_SCORE_BROADCAST"
                ]
            },
            "assets": {
                "spritesheets": [
                    {"key": "cube_tiles", "file_path": "assets/tiles/cube_rooms.png", "frame_width": 64, "frame_height": 64}
                ],
                "tilemaps": [
                    {"key": "maze_9x9", "file_path": "assets/maps/maze9x9.json", "format": "TILED_JSON"}
                ],
                "audio_banks": []
            },
            "kickback_integration": {
                "max_players": 4,
                "omnicredits_reward_rate": 2.5,
                "telemetry_events": ["ROOM_ESCAPED", "KEYCARD_FOUND"]
            }
        },
        "phaser_code_snippet": """
// 9x9 Cube Escape Logic
class CubeEscapeScene extends Phaser.Scene {
    create() {
        this.add.text(50, 30, '9x9 Cube Room [3, 7]', { fill: '#7209B7', fontSize: '20px' });
        // Render 2D grid matrix
    }
}
"""
    },
    "SOCIAL_AUDIO": {
        "template_id": "tpl_social_radio_soundboard",
        "title": "Live Broadcast Soundboard & Podcast Feed",
        "industry": "Media, Music & B2B Broadcasting",
        "description": "Interactive audio soundboard and podcast playback console integrated with Socioboard syndication.",
        "manifest": {
            "schema_version": "1.0.0",
            "mod_id": "omnimod.templates.social_radio_soundboard",
            "version": "1.0.0",
            "title": "Social Radio Soundboard",
            "description": "Broadcast soundboard and live commentary triggers.",
            "category": "audio_pack",
            "author": {
                "handle": "@kickback.radio",
                "pubkey_ed25519": "0x0000000000000000000000000000000000000000000000000000000000000005",
                "attestation_badge": "HUMAN_VERIFIED_CREATOR"
            },
            "engine_target": {
                "framework": "phaser_3_canvas",
                "min_framework_version": "3.80.0",
                "entrypoint": "src/radio_logic.js",
                "sandbox_permissions": ["CANVAS_RENDER_2D", "AUDIO_PLAYBACK"]
            },
            "assets": {
                "spritesheets": [
                    {"key": "sound_buttons", "file_path": "assets/ui/buttons.png", "frame_width": 100, "frame_height": 100}
                ],
                "tilemaps": [],
                "audio_banks": [
                    {"key": "horn_sfx", "file_path": "assets/audio/airhorn.ogg"},
                    {"key": "cheer_sfx", "file_path": "assets/audio/crowd_cheer.ogg"}
                ]
            },
            "kickback_integration": {
                "max_players": 1,
                "omnicredits_reward_rate": 0.5,
                "telemetry_events": ["SOUND_TRIGGERED", "BROADCAST_STARTED"]
            }
        },
        "phaser_code_snippet": """
// Social Radio Soundboard Logic
class SoundboardScene extends Phaser.Scene {
    create() {
        const btn = this.add.image(200, 200, 'sound_buttons', 0).setInteractive();
        btn.on('pointerdown', () => {
            this.sound.play('horn_sfx');
        });
    }
}
"""
    }
}


def export_starter_templates_pack(output_path: str = "/workspace/scratch/omni_mod_starter_templates.json"):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(TEMPLATES, f, indent=2)
    print(f"Exported Starter Templates to {path}")


if __name__ == "__main__":
    export_starter_templates_pack()
