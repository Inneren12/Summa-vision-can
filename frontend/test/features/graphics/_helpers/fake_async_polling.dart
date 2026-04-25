import 'package:fake_async/fake_async.dart';

/// Pumps [fakeAsync] until all microtasks are drained and no timers remain.
void pumpUntilIdle(FakeAsync async, {int maxTicks = 200}) {
  for (var i = 0; i < maxTicks; i++) {
    async.flushMicrotasks();
    if (async.pendingTimers.isEmpty) return;
    final nextDuration = async.pendingTimers
        .map((timer) => timer.duration)
        .reduce((a, b) => a < b ? a : b);
    async.elapse(nextDuration);
  }

  throw StateError(
    'pumpUntilIdle: not quiescent after $maxTicks ticks. '
    'Pending timers: ${async.pendingTimers.length}. '
    'Likely cause: infinite loop in notifier or real-time-only side effect.',
  );
}
