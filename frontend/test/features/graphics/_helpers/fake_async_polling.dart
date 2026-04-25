import 'package:fake_async/fake_async.dart';

/// Drains polling timers under [FakeAsync] deterministically.
void drainPollCycles(
  FakeAsync async, {
  required Duration pollInterval,
  required int pollCycles,
}) {
  async.flushMicrotasks();
  for (var i = 0; i < pollCycles; i++) {
    async.elapse(pollInterval);
    async.flushMicrotasks();
  }
}
