"""Operational metrics for the tutor processes, written to Supabase in the background.

Used by main.py (service 'tutor-web') and worker.py (service 'tutor-worker'):

    reporter = OpsReporter(sb, service="tutor-web")
    reporter.gauges["threads_busy"] = lambda: ...      # optional extra gauges
    reporter.start()
    reporter.log_request(route, method, status, duration_ms)   # web only

Two threads, both daemon, both swallow every error (metrics must never take the
service down or slow a request):
  * flush thread  — every OPS_METRICS_FLUSH_SECONDS (5) sends buffered request rows in
                    one RPC (request_log_insert). Buffer capped; overflow is dropped
                    and counted, never blocks.
  * sample thread — every OPS_METRICS_INTERVAL_SECONDS (30) inserts one service_metrics
                    row: RSS, CPU% since last sample, MemAvailable, load1, gauges.

OPS_METRICS_ENABLED=0 turns the whole thing off. Also writes the same lines to a
local file when OPS_LOG_DIR is set (default /var/log/iakids if writable), so a
crash on a box without DB access still leaves a trace.
"""
import json
import os
import socket
import threading
import time
from collections import deque
from pathlib import Path

ENABLED = os.getenv("OPS_METRICS_ENABLED", "1") not in ("0", "false", "no")
FLUSH_SECONDS = float(os.getenv("OPS_METRICS_FLUSH_SECONDS", "5"))
INTERVAL_SECONDS = float(os.getenv("OPS_METRICS_INTERVAL_SECONDS", "30"))
BUFFER_MAX = int(os.getenv("OPS_METRICS_BUFFER_MAX", "5000"))
RETENTION_DAYS = int(os.getenv("OPS_METRICS_RETENTION_DAYS", "30"))

_CLK = os.sysconf("SC_CLK_TCK") if hasattr(os, "sysconf") else 100
_PAGE = os.sysconf("SC_PAGE_SIZE") if hasattr(os, "sysconf") else 4096


def _self_stat():
    """(rss_mb, cpu_seconds) of this process from /proc; (None, None) elsewhere."""
    try:
        with open("/proc/self/stat") as f:
            parts = f.read().rsplit(")", 1)[1].split()
        cpu_s = (int(parts[11]) + int(parts[12])) / _CLK
        with open("/proc/self/statm") as f:
            rss_mb = int(f.read().split()[1]) * _PAGE // (1024 * 1024)
        return rss_mb, cpu_s
    except Exception:
        return None, None


def _mem_available_mb():
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) // 1024
    except Exception:
        pass
    return None


def _load1():
    try:
        return round(os.getloadavg()[0], 2)
    except Exception:
        return None


def _local_log_path(service: str):
    for d in (os.getenv("OPS_LOG_DIR"), "/var/log/iakids"):
        if not d:
            continue
        try:
            Path(d).mkdir(parents=True, exist_ok=True)
            p = Path(d) / f"{service}.metrics.log"
            with open(p, "a"):
                pass
            return p
        except Exception:
            continue
    return None


class OpsReporter:
    def __init__(self, sb, service: str, instance: str | None = None):
        self.sb = sb
        self.service = service
        self.instance = instance or f"{socket.gethostname()}:{os.getpid()}"
        self.gauges = {}                       # name -> callable returning a number (or None)
        self._buf = deque()
        self._lock = threading.Lock()
        self.dropped = 0
        self._last_cpu = None
        self._last_err = 0.0
        self._started = False
        self._local = _local_log_path(service)
        self._last_prune = 0.0

    # ---------------------------------------------------------------- requests
    def log_request(self, route, method, status, duration_ms, user_id=None, kid_id=None, extra=None):
        if not ENABLED:
            return
        row = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()), "service": self.service,
               "instance": self.instance, "route": route, "method": method, "status": int(status),
               "duration_ms": int(duration_ms), "user_id": user_id, "kid_id": kid_id, "extra": extra}
        with self._lock:
            if len(self._buf) >= BUFFER_MAX:
                self.dropped += 1
                return
            self._buf.append(row)

    # ---------------------------------------------------------------- lifecycle
    def start(self):
        if not ENABLED or self._started:
            return self
        self._started = True
        threading.Thread(target=self._flush_loop, name="ops-flush", daemon=True).start()
        threading.Thread(target=self._sample_loop, name="ops-sample", daemon=True).start()
        self._print("up", instance=self.instance, local_log=str(self._local))
        return self

    def sample_now(self):
        """One service_metrics row, synchronously. Used by the sample thread and tests."""
        rss, cpu_s = _self_stat()
        now = time.time()
        cpu_pct = None
        if cpu_s is not None and self._last_cpu is not None:
            cpu_pct = round(100.0 * (cpu_s - self._last_cpu[1]) / max(0.001, now - self._last_cpu[0]), 1)
        if cpu_s is not None:
            self._last_cpu = (now, cpu_s)
        row = {"service": self.service, "instance": self.instance, "rss_mb": rss, "cpu_pct": cpu_pct,
               "mem_available_mb": _mem_available_mb(), "load1": _load1()}
        extra = {}
        for name, fn in list(self.gauges.items()):
            try:
                v = fn()
            except Exception as e:
                v = None; extra[name + "_error"] = repr(e)[:120]
            if name in ("threads_busy", "jobs_running", "queue_pending"):
                row[name] = v
            else:
                extra[name] = v
        if self.dropped:
            extra["request_rows_dropped"] = self.dropped
        row["extra"] = extra or None
        self._local_write("sample", row)
        self.sb.table("service_metrics").insert(row).execute()
        return row

    # ---------------------------------------------------------------- internals
    def _flush(self):
        with self._lock:
            if not self._buf:
                return 0
            rows = list(self._buf)
            self._buf.clear()
        self.sb.rpc("request_log_insert", {"p_rows": rows}).execute()
        return len(rows)

    def _flush_loop(self):
        while True:
            time.sleep(FLUSH_SECONDS)
            try:
                self._flush()
            except Exception as e:
                self._err("request_log flush failed", e)

    def _sample_loop(self):
        _self_stat()                                 # prime the CPU counter
        while True:
            try:
                self.sample_now()
            except Exception as e:
                self._err("service_metrics sample failed", e)
            if self.service.endswith("worker") and time.time() - self._last_prune > 86400:
                self._last_prune = time.time()
                try:
                    n = self.sb.rpc("ops_metrics_prune", {"p_days": RETENTION_DAYS}).execute().data
                    self._print("pruned old metrics", rows=n, retention_days=RETENTION_DAYS)
                except Exception as e:
                    self._err("prune failed", e)
            time.sleep(INTERVAL_SECONDS)

    def _err(self, msg, e):
        if time.time() - self._last_err > 60:          # one line a minute, not one per failure
            self._last_err = time.time()
            self._print(msg, error=repr(e)[:200])

    def _print(self, event, **kv):
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} [ops {self.service}] {event}", kv if kv else "", flush=True)
        self._local_write(event, kv)

    def _local_write(self, event, data):
        if not self._local:
            return
        try:
            with open(self._local, "a") as f:
                f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "event": event, **(data or {})},
                                   ensure_ascii=False, default=str) + "\n")
        except Exception:
            pass
