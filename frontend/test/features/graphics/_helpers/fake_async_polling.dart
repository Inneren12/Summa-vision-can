import 'package:fake_async/fake_async.dart';

/// Pumps [fakeAsync] until all microtasks are drained and no timers remain.
///
/// Default [maxTicks] is generous (500) to cover full poll loops with nested
/// microtask chains: a single poll iteration may enqueue 3-5 microtasks
/// (HTTP mock resolve → JSON decode → state update → listener notify), and
/// chart generation has up to 60 polls. 60 × 5 = 300, plus margin → 500.
void pumpUntilIdle(FakeAsync async, {int maxTicks = 500}) {
  for (var i = 0; i < maxTicks; i++) {
    async.flushMicrotasks();
    if (async.pendingTimers.isEmpty) return;
    final nextDuration = async.pendingTimers
        .map((timer) => timer.duration)
        .reduce((a, b) => a < b ? a : b);
    async.elapse(nextDuration);
  }

  final timerSummary = async.pendingTimers
      .take(10)
      .map((t) => '${t.duration.inMilliseconds}ms')
      .join(', ');
  throw StateError(
    'pumpUntilIdle: not quiescent after $maxTicks ticks. '
    '${async.pendingTimers.length} pending timers: $timerSummary. '
    'Likely cause: infinite poll loop, real-time-only side effect, or '
    'maxTicks too low for the depth of the async chain.',
  );
}
