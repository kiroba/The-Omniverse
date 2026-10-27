import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:ota_update/ota_update.dart';

import 'canonical_json.dart';
import 'stargate_identity.dart';

/// ============================================================================
/// OMNI OTA ENGINE (omni_core_ui)
/// ============================================================================
/// In-app over-the-air updates for every Omniverse APK.
///
/// Today the update source is GitHub Releases (free hosting). Every tagged
/// release publishes `update-manifest.json`:
///   { "tag": "v0.1.3", "build": 1012, "transport": "github",
///     "apps": { "mesh-monitor": { "url": "...apk", "sha256": "..." }, ... } }
///
/// The app compares the manifest `build` with its own build number (baked in at
/// compile time with --dart-define=OMNI_BUILD=...). If newer, it offers the
/// update, downloads the APK, verifies its SHA-256 and opens Android's install
/// prompt. Releases share one signing key, so the update installs over the top.
///
/// Signed manifests: when the release workflow has the OMNI_OTA_SIGNING_KEY
/// secret, it signs the manifest (Ed25519 over the canonical JSON of the
/// manifest minus "signature") and bakes the public key into every APK with
/// --dart-define=OMNI_OTA_PUBKEY=<hex>. A build that has a public key refuses
/// any manifest that isn't signed by it. That matters most once peers serve
/// updates over OmniNet, since a peer is not trusted the way GitHub is.
///
/// OmniNet: once the mesh transport is live, peers will serve the same manifest
/// and APK bytes and become the primary source; GitHub stays as the fallback.
/// Add those sources to [OmniOta.manifestSources] ahead of GitHub.
/// ============================================================================

class OmniOta {
  /// Short app name, matching the release asset (e.g. "mesh-monitor").
  static const String appSlug = String.fromEnvironment('OMNI_APP', defaultValue: 'unknown');

  /// This build's number (1000 + release workflow run). 0 = local dev build.
  static const int currentBuild = int.fromEnvironment('OMNI_BUILD', defaultValue: 0);

  /// Where to look for the manifest, in priority order.
  /// OmniNet peer sources go first here once the mesh transport exists.
  static const List<String> manifestSources = [
    'https://github.com/kiroba/The-Omniverse/releases/latest/download/update-manifest.json',
  ];

  /// Ed25519 public key (64 hex) that must sign the manifest. Empty = unsigned
  /// manifests accepted (HTTPS + SHA-256 only).
  static const String otaPubkey = String.fromEnvironment('OMNI_OTA_PUBKEY', defaultValue: '');

  static bool _checkedThisSession = false;

  /// True when the manifest's signature checks out, or no key is pinned.
  static Future<bool> manifestTrusted(Map<String, dynamic> manifest) async {
    if (otaPubkey.isEmpty) return true;
    final sig = manifest['signature'];
    if (sig is! String) return false;
    final unsigned = Map<String, dynamic>.from(manifest)..remove('signature');
    return StargateIdentity.verifyBytes(utf8.encode(canonicalJson(unsigned)), sig, otaPubkey);
  }

  /// Fetches the first manifest that answers. Returns null if none do.
  static Future<Map<String, dynamic>?> fetchManifest() async {
    for (final src in manifestSources) {
      final client = HttpClient()..connectionTimeout = const Duration(seconds: 6);
      try {
        final req = await client.getUrl(Uri.parse(src));
        final res = await req.close().timeout(const Duration(seconds: 10));
        if (res.statusCode != 200) continue;
        final body = await res.transform(utf8.decoder).join();
        final decoded = jsonDecode(body);
        if (decoded is Map<String, dynamic> && await manifestTrusted(decoded)) return decoded;
      } catch (_) {
        // try the next source
      } finally {
        client.close(force: true);
      }
    }
    return null;
  }

  /// Checks for an update and, if one exists, asks the user to install it.
  /// [silent]: no message when already up to date or offline (use on startup).
  static Future<void> checkAndPrompt(BuildContext context, {bool silent = false}) async {
    if (silent && _checkedThisSession) return;
    _checkedThisSession = true;

    final messenger = ScaffoldMessenger.maybeOf(context);
    final manifest = await fetchManifest();
    if (manifest == null) {
      if (!silent) messenger?.showSnackBar(const SnackBar(content: Text('Could not reach the update server.')));
      return;
    }

    final latestBuild = (manifest['build'] is int) ? manifest['build'] as int : int.tryParse('${manifest['build']}') ?? 0;
    final apps = manifest['apps'];
    final entry = (apps is Map) ? apps[appSlug] : null;
    final tag = '${manifest['tag'] ?? ''}';

    if (entry is! Map || entry['url'] == null || latestBuild <= currentBuild) {
      if (!silent) {
        messenger?.showSnackBar(SnackBar(
          content: Text(currentBuild == 0
              ? 'Dev build: updates are only checked on release builds.'
              : 'You are up to date ($tag).'),
        ));
      }
      return;
    }
    if (currentBuild == 0) return; // never auto-replace a local dev build

    if (!context.mounted) return;
    final accept = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Update available'),
        content: Text('Omniverse $tag (build $latestBuild) is ready.\n'
            'You have build $currentBuild.\n\n'
            'It downloads, gets checked (SHA-256), then Android asks you to install.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Later')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Update')),
        ],
      ),
    );
    if (accept != true || !context.mounted) return;

    _runUpdate(context, '${entry['url']}', entry['sha256']?.toString());
  }

  static void _runUpdate(BuildContext context, String url, String? sha256) {
    final progress = ValueNotifier<String>('Starting download...');
    showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        title: const Text('Updating'),
        content: ValueListenableBuilder<String>(
          valueListenable: progress,
          builder: (_, value, __) => Text(value),
        ),
        actions: [
          TextButton(
            onPressed: () {
              OtaUpdate().cancel();
              Navigator.pop(ctx);
            },
            child: const Text('Close'),
          ),
        ],
      ),
    );

    try {
      OtaUpdate()
          .execute(
            url,
            destinationFilename: '$appSlug-update.apk',
            sha256checksum: (sha256 == null || sha256.isEmpty) ? null : sha256,
          )
          .listen(
        (OtaEvent event) {
          switch (event.status) {
            case OtaStatus.DOWNLOADING:
              progress.value = 'Downloading... ${event.value ?? 0}%';
              break;
            case OtaStatus.INSTALLING:
              progress.value = 'Verified. Opening the Android installer...';
              break;
            case OtaStatus.CHECKSUM_ERROR:
              progress.value = 'Checksum mismatch: the download was rejected.';
              break;
            case OtaStatus.PERMISSION_NOT_GRANTED_ERROR:
              progress.value = 'Allow "Install unknown apps" for this app, then try again.';
              break;
            default:
              progress.value = 'Update stopped: ${event.status.name}${event.value == null ? '' : ' (${event.value})'}';
          }
        },
        onError: (Object e) => progress.value = 'Update failed: $e',
      );
    } catch (e) {
      progress.value = 'Update failed: $e';
    }
  }
}
