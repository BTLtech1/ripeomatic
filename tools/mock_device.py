#!/usr/bin/env python3
"""A fake Ripe-O-Matic on http://localhost:8080 for working on the web page without hardware.

    python3 tools/mock_device.py            # then open http://localhost:8080
    python3 tools/mock_device.py --port 9000

It serves firmware/ui/index.html and answers the same JSON API as firmware/ripeomatic/web.h,
with a virtual avocado that softens over a few (compressed) days. Measurements run for a
few seconds so the live view can be seen.
"""
import argparse
import json
import math
import pathlib
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ROOT = pathlib.Path(__file__).resolve().parent.parent
UI = ROOT / "firmware" / "ui" / "index.html"
HEADER = ("schema,device_id,fw_version,hw_version,timestamp,fruit_id,variety,fruit_mass_g,room_temp_c,"
          "contact_pos_mm,stiffness_n_per_mm,squish_at_cap_mm,force_cap_n,blade_k_n_per_mm,cal_points,curve,"
          "human_rating,cut_open,notes")

settings = {
    "device_id": "a3f9c2", "host": "ripeomatic", "wifi_ssid": "HomeWifi", "ntfy_server": "https://ntfy.sh", "ntfy_topic": "",
    "notify_nearly": True, "variety": "hass", "auto_enabled": True, "interval_h": 12.0, "steps_per_mm": 2048.0, "motor_invert": False,
    "fast_mm_s": 0.45, "creep_mm_s": 0.25, "hall_n_per_count": 0.0035, "cal_zero_counts": 2001.0, "cal_points": "",
    "contact_threshold_n": 0.1, "preload_force_n": 0.2, "force_cap_n": 2.5, "blade_k_n_per_mm": 0.0, "sample_step_mm": 0.05,
    "approach_step_mm": 0.5, "safety_margin_mm": 2.0, "max_travel_mm": 42.0, "max_squish_mm": 12.0, "ripe_abs_n_per_mm": 1.5,
    "ripe_pct_of_first": 45.0, "swap_contact_mm": 6.0, "swap_stiffer_pct": 60.0, "servo_rest_deg": 0, "servo_tip_deg": 110,
    "servo_hold_ms": 1500, "wifi_pass_set": True, "ntfy_ok": False, "motor_checked": False,
}
notify = {"pending": False, "last_ok": False}
state = {
    "job": "idle", "stage": "idle", "pos": 0.0, "force": 0.0, "raw": 2001.0, "error": "",
    "fruit": {"counter": 7, "loaded": False, "n": 0, "first_k": 0.0, "last_k": 0.0, "first_contact": 0.0, "last_contact": 0.0, "start": 0.0, "rating": "", "nr": False},
    "last": {"outcome": "none", "time": "", "k": 0, "r2": 0, "squish": 0, "contact": 0, "force_max": 0, "n_points": 0},
    "pts": [], "rows": [], "boot": time.time(), "last_measure": 0.0,
}
LOCK = threading.Lock()
DAY_SECONDS = 60.0   # one virtual day per minute so the trend fills in while you watch


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def fruit_id():
    return f"{settings['device_id']}-{state['fruit']['counter']:04d}"


def virtual_k():
    f = state["fruit"]
    if not f["start"]:
        return 6.0
    days = (time.time() - f["start"]) / DAY_SECONDS
    return 1.0 + 5.0 * math.exp(-days / 2.5)


def threshold():
    f = state["fruit"]
    thr = settings["ripe_abs_n_per_mm"]
    if settings["ripe_pct_of_first"] > 0 and f["first_k"] > 0:
        thr = max(thr, f["first_k"] * settings["ripe_pct_of_first"] / 100)
    return thr


def verdict(k, first):
    if k <= 0:
        return "unknown"
    thr = threshold()
    if thr <= 0:
        return "unknown"
    if k <= thr:
        return "ripe"
    if k <= thr * 1.3:
        return "nearly"
    if first > 0 and k < first * 0.8:
        return "firming"
    return "hard"


def run_measure(blade_cal=False):
    stages = [("homing", 0.6), ("taring", 0.3), ("approach", 0.8), ("creep", 0.8), ("preload", 0.3)]
    for name, dur in stages:
        with LOCK:
            state["stage"] = name
            state["pos"] = {"homing": 0, "taring": 0, "approach": 18, "creep": 23.9, "preload": 24.1}[name]
            state["force"] = 0.0 if name in ("homing", "taring", "approach") else 0.1
        time.sleep(dur)
    k_fruit = 3.2 if blade_cal else virtual_k()
    k_blade = 3.2
    k_series = k_blade if blade_cal else k_fruit * k_blade / (k_fruit + k_blade)
    pts = []
    cap = settings["force_cap_n"]
    bk = settings["blade_k_n_per_mm"] if not blade_cal else 0
    pos = 24.1
    force = 0.2
    with LOCK:
        state["stage"] = "measure"
        state["pts"] = pts
    while force < cap:
        pos += 0.05
        force = (pos - 24.0) * k_series + random.uniform(-0.02, 0.02)
        travel = pos - 24.1
        bend = (force - 0.2) / bk if bk > 0.01 else 0
        pts.append([max(0, travel - bend), force])
        with LOCK:
            state["pos"] = pos
            state["force"] = force
        time.sleep(0.08)
    with LOCK:
        state["stage"] = "retract"
    time.sleep(0.5)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    n = len(xs)
    sx, sy = sum(xs), sum(ys)
    sxx, sxy = sum(x * x for x in xs), sum(x * y for x, y in zip(xs, ys))
    slope = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    with LOCK:
        state["pos"] = 0
        state["force"] = 0
        state["last_measure"] = time.time()
        if blade_cal:
            settings["blade_k_n_per_mm"] = round(slope, 2)
            state["last"].update({"outcome": "reading", "time": now_iso(), "k": slope, "r2": 0.999, "n_points": n})
            return
        f = state["fruit"]
        if not f["loaded"]:
            f.update({"counter": f["counter"] + 1, "loaded": True, "n": 0, "first_k": slope, "first_contact": 24.0, "start": time.time(), "rating": "", "nr": False})
        f["n"] += 1
        f["last_k"] = slope
        f["last_contact"] = 24.0
        f["rating"] = ""
        state["last"].update({"outcome": "reading", "time": now_iso(), "k": slope, "r2": 0.998, "squish": xs[-1], "contact": 24.0, "force_max": ys[-1], "n_points": n})
        curve = ";".join(f"{x:.2f}:{y:.2f}" for x, y in pts[:: max(1, n // 24)])
        # stretch the timestamp so one virtual day (DAY_SECONDS) shows as a real day on the chart
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(f["start"] + (time.time() - f["start"]) * (86400 / DAY_SECONDS)))
        state["rows"].append(f"1,{settings['device_id']},0.1.0,v1,{ts},{fruit_id()},{settings['variety']},,,24.00,{slope:.3f},{xs[-1]:.2f},{cap:.2f},{bk or ''},,{curve},,,")


def start_job(job, fn):
    with LOCK:
        if state["job"] != "idle":
            return False
        state["job"] = job
        state["error"] = ""

    def runner():
        try:
            fn()
        finally:
            with LOCK:
                state["job"] = "idle"
                state["stage"] = "idle"
    threading.Thread(target=runner, daemon=True).start()
    return True


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj))

    def _form(self):
        n = int(self.headers.get("Content-Length") or 0)
        return {k: v[0] for k, v in parse_qs(self.rfile.read(n).decode()).items()}

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if u.path in ("/", "/index.html"):
            return self._send(200, UI.read_bytes(), "text/html")
        if u.path == "/manifest.json":
            return self._send(200, '{"name":"Ripe-O-Matic","short_name":"Ripe-O-Matic","start_url":"/","display":"standalone"}', "application/manifest+json")
        if u.path == "/icon.svg":
            return self._send(200, '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#2e4a21"/></svg>', "image/svg+xml")
        if u.path == "/sw.js":
            return self._send(200, "self.addEventListener('fetch',e=>{});", "application/javascript")
        if u.path == "/api/status":
            with LOCK:
                f = state["fruit"]
                days = (time.time() - f["start"]) / DAY_SECONDS if f["loaded"] and f["start"] else None
                thr = threshold()
                v = verdict(f["last_k"], f["first_k"]) if f["loaded"] else "unknown"
                d2r = -1
                if f["loaded"] and days and days > 0.5 and f["last_k"] > 0 and f["last_k"] < f["first_k"] * 0.98:
                    rate = math.log(f["first_k"] / f["last_k"]) / days
                    d2r = 0 if f["last_k"] <= thr else min(30, math.log(f["last_k"] / thr) / rate)
                nxt = -1
                if settings["auto_enabled"]:
                    due = (state["last_measure"] or state["boot"]) + (settings["interval_h"] * 3600 if state["last_measure"] else 60)
                    nxt = max(0, int(due - time.time()))
                return self._json(200, {
                    "fw": "0.1.0-mock", "hw": "v1", "device_id": settings["device_id"], "host": settings["host"], "ip": "192.168.1.42",
                    "ap_mode": False, "ap_ssid": "", "rssi": -58, "time": now_iso(), "uptime_s": int(time.time() - state["boot"]),
                    "job": state["job"], "stage": state["stage"], "pos_mm": state["pos"], "force_n": state["force"], "raw": state["raw"] + state["force"] / settings["hall_n_per_count"],
                    "calibrated": bool(settings["cal_points"]), "n_per_count": settings["hall_n_per_count"], "cal_points_n": settings["cal_points"].count(":"),
                    "blade_calibrated": settings["blade_k_n_per_mm"] > 0.01, "blade_k": settings["blade_k_n_per_mm"], "setup_done": bool(settings["cal_points"]) and settings["blade_k_n_per_mm"] > 0.01, "servo": False,
                    "simulate": False, "ntfy_topic": settings["ntfy_topic"], "ntfy_ok": settings["ntfy_ok"], "notify_pending": notify["pending"], "notify_last_ok": notify["last_ok"],
                    "motor_checked": settings["motor_checked"], "motor_invert": settings["motor_invert"], "online": True, "fruit_count": f["counter"],
                    "log_bytes": sum(len(r) + 1 for r in state["rows"]), "fs_free": 1400000, "next_auto_s": nxt, "error": state["error"],
                    "fruit": {"id": fruit_id(), "loaded": f["loaded"], "n": f["n"], "first_k": f["first_k"], "last_k": f["last_k"],
                              "first_contact": f["first_contact"], "last_contact": f["last_contact"], "start_epoch": int(f["start"]),
                              **({"elapsed_days": days} if days is not None else {}), "threshold": thr, "verdict": v, "days_to_ripe": d2r,
                              "rating": f["rating"], "ripe_notified": f["nr"]},
                    "last": state["last"],
                })
        if u.path == "/api/live":
            with LOCK:
                return self._json(200, {"stage": state["stage"], "pos": state["pos"], "force": state["force"], "k": state["last"]["k"], "r2": state["last"]["r2"], "pts": state["pts"]})
        if u.path == "/api/settings":
            return self._json(200, settings)
        if u.path == "/api/scan":
            return self._json(200, {"networks": [{"ssid": "HomeWifi", "rssi": -58, "open": False}, {"ssid": "Neighbour", "rssi": -80, "open": True}]})
        if u.path == "/data.csv":
            with LOCK:
                rows = state["rows"]
                if q.get("fruit", "current") != "all":
                    rows = [r for r in rows if r.split(",")[5] == fruit_id()]
                return self._send(200, HEADER + "\n" + "".join(r + "\n" for r in rows), "text/csv")
        self._send(404, "not found", "text/plain")

    def do_POST(self):
        u = urlparse(self.path)
        d = self._form()
        busy = state["job"] != "idle"
        if u.path == "/api/measure":
            return self._json(200, {"ok": True}) if start_job("measure", run_measure) else self._json(409, {"ok": False, "error": "busy"})
        if u.path == "/api/newfruit":
            if busy:
                return self._json(409, {"ok": False, "error": "busy"})
            with LOCK:
                state["fruit"].update({"loaded": False, "n": 0, "first_k": 0, "last_k": 0, "start": 0})
            start_job("measure", run_measure)
            return self._json(200, {"ok": True})
        if u.path == "/api/abort":
            return self._json(200, {"ok": True})
        if u.path == "/api/home":
            return self._json(200, {"ok": True}) if start_job("home", lambda: time.sleep(1.5)) else self._json(409, {"ok": False, "error": "busy"})
        if u.path == "/api/jog":
            mm = float(d.get("mm", 0))
            if mm == 0 or abs(mm) > 20:
                return self._json(400, {"ok": False, "error": "mm must be within +-20"})

            def jog():
                with LOCK:
                    state["pos"] = max(0, state["pos"] + mm)
                time.sleep(abs(mm) / 0.45)
            return self._json(200, {"ok": True}) if start_job("jog", jog) else self._json(409, {"ok": False, "error": "busy"})
        if u.path == "/api/tip":
            return self._json(400, {"ok": False, "error": "servo not enabled in this build (config.h ENABLE_SERVO)"})
        if u.path == "/api/rate":
            r = d.get("r", "")
            if r not in ("hard", "firm", "ready", "perfect", "overripe"):
                return self._json(400, {"ok": False, "error": "bad rating"})
            with LOCK:
                state["fruit"]["rating"] = r
                state["rows"].append(f"1,{settings['device_id']},0.1.0,v1,{now_iso()},{fruit_id()},{settings['variety']},,,,,,,,,,{r},{d.get('cut', '')},{d.get('notes', '')}")
            return self._json(200, {"ok": True})
        if u.path == "/api/cal/zero":
            settings["cal_points"] = ""
            return self._json(200, {"ok": True, "raw": 2001})
        if u.path == "/api/cal/mass":
            g = float(d.get("g", 0))
            if g <= 0:
                return self._json(400, {"ok": False, "error": "bad mass"})
            settings["cal_points"] += ("" if not settings["cal_points"] else ";") + f"{g:.1f}:{2001 + g / 1000 * 9.81 / 0.0035:.0f}"
            return self._json(200, {"ok": True, "n_per_count": 0.0035})
        if u.path == "/api/ntfy/new":
            settings["ntfy_topic"] = f"ripe-{settings['device_id']}-{random.randrange(10**6):06d}"
            settings["ntfy_ok"] = False
            return self._json(200, {"ok": True, "topic": settings["ntfy_topic"]})
        if u.path == "/api/ntfy/test":
            if not settings["ntfy_topic"]:
                return self._json(400, {"ok": False, "error": "no topic set"})
            notify["pending"] = True

            def deliver():
                time.sleep(1.5)
                settings["ntfy_ok"] = True
                notify.update({"pending": False, "last_ok": True})
            threading.Thread(target=deliver, daemon=True).start()
            return self._json(200, {"ok": True})
        if u.path == "/api/motor/checked":
            if d.get("ok") == "0":
                settings["motor_invert"] = not settings["motor_invert"]
                settings["motor_checked"] = False
            else:
                settings["motor_checked"] = True
            return self._json(200, {"ok": True})
        if u.path == "/api/cal/clear":
            settings["cal_points"] = ""
            return self._json(200, {"ok": True})
        if u.path == "/api/cal/blade":
            return self._json(200, {"ok": True}) if start_job("bladecal", lambda: run_measure(True)) else self._json(409, {"ok": False, "error": "busy"})
        if u.path == "/api/settings":
            unknown = 0
            for k, v in d.items():
                if k in settings and k not in ("device_id", "wifi_ssid", "wifi_pass"):
                    cur = settings[k]
                    settings[k] = (v in ("1", "true", "on")) if isinstance(cur, bool) else type(cur)(v) if isinstance(cur, (int, float)) else v
                else:
                    unknown += 1
            return self._json(200, {"ok": True, "unknown": unknown, "reboot_needed": False})
        if u.path == "/api/wifi":
            return self._json(200, {"ok": True}) if d.get("ssid") else self._json(400, {"ok": False, "error": "ssid required"})
        if u.path == "/api/reset":
            w = d.get("what")
            with LOCK:
                if w in ("fruit", "data"):
                    state["fruit"].update({"loaded": False, "n": 0, "first_k": 0, "last_k": 0, "start": 0, "rating": ""})
                if w == "data":
                    state["rows"].clear()
            return self._json(200, {"ok": True}) if w in ("fruit", "data", "settings", "all") else self._json(400, {"ok": False, "error": "what = fruit | data | settings | all"})
        if u.path == "/api/reboot":
            return self._json(200, {"ok": True})
        self._json(404, {"ok": False, "error": "not found"})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8080)
    a = ap.parse_args()
    print(f"mock Ripe-O-Matic on http://localhost:{a.port}  (Ctrl-C to stop)")
    ThreadingHTTPServer(("", a.port), H).serve_forever()
