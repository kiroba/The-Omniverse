import 'package:flutter_test/flutter_test.dart';
import 'package:omni_core_ui/omni_core_ui.dart';

import '../../../mobile/lib/omni_signal_client.dart';

// The app's one identity (StargateIdentity) signs OmniCast signaling bytes via
// signBytes, and the result equals the Python daemon's vector (seed 0..31).
// Vector source: Admin/omni_live_daemon_server.py signal_send_bytes (desktop,
// v8.11.0); same values as omni_signal_client_test.dart and
// tests/test_signal_mailbox.py SignalVectorTests.
void main() {
  test('StargateIdentity.signBytes matches the Python signaling vector', () async {
    final id = await StargateIdentity.fromSeed(List<int>.generate(32, (i) => i));
    expect(id.pubkeyHex, '03a107bff3ce10be1d70dd18e74bc09967e4d6309ba50d5f1ddc8664125531b8');
    final bytes = signalSendBytes(
      to: '29acbae141bccaf0b22e1a94d34d0bc7361e526d0bfe12c89794bc9322966dd7',
      from: id.pubkeyHex,
      callId: 'call-vector_1.a:b',
      kind: 'offer',
      payload: 'v=0\r\no=- 46117 2 IN IP4 127.0.0.1\r\ns=K\u00edro \u{1F3A7} "q" \\ /\t\u2028\u0001\u007f\r\n',
      ts: 1793042651190,
    );
    final sig = await id.signBytes(bytes);
    expect(sig,
        'afe1e65c40101a39de0e9f12882ff6fc42bcee1f1d2839637ad27664f5cc7d6b67fe3f3e923d7bbd5aa643a71ff0e322c733aea0435c0a96eefe96c210060209');
    expect(await verifySignalSignature(bytes, sig, id.pubkeyHex), isTrue);
    // and the client accepts it as its signer
    final client = OmniSignalClient(hub: const SignalHub.loopback(), pubkeyHex: id.pubkeyHex, sign: id.signBytes);
    expect(client.pubkeyHex, id.pubkeyHex);
  });
}
