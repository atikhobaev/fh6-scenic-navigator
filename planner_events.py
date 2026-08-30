from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import queue
import threading


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class PlannerEventBus:
    def __init__(self):
        self._lock=threading.Lock(); self._subs=set(); self._seq=0

    @contextmanager
    def subscribe(self):
        q=queue.Queue(maxsize=128)
        with self._lock: self._subs.add(q)
        try: yield q
        finally:
            with self._lock: self._subs.discard(q)

    def publish(self, event_type: str, payload: dict):
        with self._lock:
            self._seq += 1
            evt={'id':self._seq,'type':event_type,'payload':dict(payload),'created_at':now_iso()}
            subs=list(self._subs)
        for q in subs:
            try: q.put_nowait(evt)
            except queue.Full:
                try: q.get_nowait(); q.put_nowait(evt)
                except queue.Empty: pass
        return evt
