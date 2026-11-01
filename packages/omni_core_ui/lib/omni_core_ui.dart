/// Omniverse shared app core.
///
/// One door out: apps never talk to peers directly. Everything leaves the
/// device through the Omni-Hub (the local daemon on loopback), which signs,
/// stores and relays events to the wider OmniNet. See [OmniHubClient].
library omni_core_ui;

export 'src/canonical_json.dart';
export 'src/stargate_identity.dart';
export 'src/local_event_store.dart';
export 'src/omni_hub_client.dart';
export 'src/hub_feed.dart';
export 'src/hub_credits.dart';
export 'src/omni_ota_engine.dart';
export 'src/human_badges.dart';
