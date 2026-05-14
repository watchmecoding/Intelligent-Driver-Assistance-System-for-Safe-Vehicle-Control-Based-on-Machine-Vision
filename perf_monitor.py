# perf_monitor.py
import time
import statistics
import logging
from collections import defaultdict


class PerfMonitor:
    def __init__(self, report_every=300, log_path="logs/perf_metrics.log", also_print=False):
        self.report_every = report_every
        self.frame_idx = 0
        self.samples = defaultdict(list)
        self.event_timers = {}
        self.pending_cmd = {}
        self.also_print = also_print

        logger_name = f"perf_metrics_{id(self)}"
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        if not self.logger.handlers:
            fh = logging.FileHandler(log_path, mode="a", encoding="utf-8")
            fh.setLevel(logging.INFO)
            fh.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
            self.logger.addHandler(fh)

    def _log(self, message):
        self.logger.info(message)
        if self.also_print:
            print(message)

    def tic(self):
        return time.perf_counter()

    def toc_ms(self, t0):
        return (time.perf_counter() - t0) * 1000.0

    def add(self, name, value_ms):
        self.samples[name].append(value_ms)

    def mark_event_start(self, name):
        if self.event_timers.get(name) is None:
            self.event_timers[name] = time.perf_counter()

    def clear_event_start(self, name):
        self.event_timers[name] = None

    def mark_command_sent(self, cmd_name, event_name=None):
        now = time.perf_counter()

        if event_name and self.event_timers.get(event_name) is not None:
            latency_ms = (now - self.event_timers[event_name]) * 1000.0
            self.add(f"{event_name}_to_cmd_ms", latency_ms)
            self._log(f"{event_name} -> {cmd_name}: {latency_ms:.2f} ms")

        self.pending_cmd[cmd_name] = now

    def mark_ack(self, cmd_name):
        t0 = self.pending_cmd.get(cmd_name)
        if t0 is not None:
            ack_ms = (time.perf_counter() - t0) * 1000.0
            self.add(f"{cmd_name.lower()}_ack_ms", ack_ms)
            self._log(f"{cmd_name} ACK latency: {ack_ms:.2f} ms")
            self.pending_cmd.pop(cmd_name, None)

    def report(self):
        lines = [f"--- PERF REPORT @ frame {self.frame_idx} ---"]

        for name, vals in self.samples.items():
            chunk = vals[-self.report_every:]
            if not chunk:
                continue

            avg = sum(chunk) / len(chunk)
            med = statistics.median(chunk)
            p95 = sorted(chunk)[max(0, int(len(chunk) * 0.95) - 1)]

            lines.append(
                f"{name:24s} "
                f"avg={avg:7.2f} ms | "
                f"med={med:7.2f} ms | "
                f"p95={p95:7.2f} ms | "
                f"min={min(chunk):7.2f} ms | "
                f"max={max(chunk):7.2f} ms"
            )

        self._log("\n".join(lines))

    def next_frame(self):
        self.frame_idx += 1
        if self.frame_idx % self.report_every == 0:
            self.report()