#!/usr/bin/env python3
# Automatic SkillSpector scan of user-added skills. Modes: start | report | worker.
import glob, hashlib, json, os, subprocess, sys
H = os.path.expanduser("~"); C = H + "/.claude"; OUT = H + "/.cache/skill-scan"
SS = H + "/.local/bin/skillspector"; LOCK = OUT + "/worker.lock"
def targets():
    t = {}
    for m in glob.glob(C + "/skills/synced/*/manifest.json"):
        for s in json.load(open(m)).get("skills", []):
            if s.get("source") not in ("anthropic", "anthropic-example"):
                t[s["name"]] = os.path.join(os.path.dirname(m), s["name"])
    for m in glob.glob(C + "/plugins/synced/*/manifest.json"):
        for p in json.load(open(m)).get("plugins", []):
            t["plugin:" + p["name"]] = os.path.join(os.path.dirname(m), p["name"])
    return {n: d for n, d in t.items() if os.path.isdir(d)}
def digest(d):
    h = hashlib.sha256()
    for f in sorted(glob.glob(d + "/**", recursive=True, include_hidden=True)):
        if os.path.isfile(f) and ".in_use" not in (r := os.path.relpath(f, d)).split(os.sep) and "__pycache__" not in f:
            h.update(r.encode() + open(f, "rb").read())
    return h.hexdigest()[:16]
def pending():
    p = {n: (d, digest(d)) for n, d in targets().items()}
    return {n: v for n, v in p.items() if not os.path.exists(f"{OUT}/{v[1]}.json")}
def worker():
    try: fd = os.open(LOCK, os.O_CREAT | os.O_EXCL)
    except FileExistsError: return
    try:
        for n, (d, k) in pending().items():
            tmp = f"{OUT}/{k}.tmp"
            try: subprocess.run([SS, "scan", d, "--no-llm", "--format", "json", "--output", tmp],
                                capture_output=True, timeout=900)
            except subprocess.TimeoutExpired: pass
            r = json.load(open(tmp)) if os.path.exists(tmp) else {"risk_assessment":
                {"severity": "SCAN_FAILED", "recommendation": "REVIEW_MANUALLY"}}
            r["_name"], r["_dir"] = n, d
            json.dump(r, open(f"{OUT}/{k}.json", "w"))
            os.path.exists(tmp) and os.remove(tmp)
    finally: os.close(fd); os.remove(LOCK)
def report():
    lines, ok = [], json.load(open(C + "/skill-scan/reviewed.json"))
    for f in sorted(glob.glob(OUT + "/*.json")):
        if os.path.exists(f + ".reported"): continue
        open(f + ".reported", "w").close(); r = json.load(open(f)); a = r.get("risk_assessment", {})
        rv = ok.get(r["_name"], {}); rv = rv if rv.get("digest") == os.path.basename(f)[:-5] else {}
        st = f"ALREADY REVIEWED, unchanged: {rv['verdict']} ({rv['note']})" if rv else "NEW/CHANGED, needs review"
        lines.append(f"- {r['_name']}: {st}. score {a.get('score')} {a.get('severity')} "
                     f"{a.get('recommendation')} (report: {f}, folder: {r['_dir']})")
    if lines:
        print("Automatic SkillSpector results for user-added skills. Follow the 'New skill safety "
              "check' rule in CLAUDE.md. For NEW/CHANGED entries, review every HIGH/CRITICAL "
              "finding and give an APPROVE/CAUTION/REJECT verdict before using the skill:")
        print("\n".join(lines))
def main():
    os.makedirs(OUT, exist_ok=True); mode = (sys.argv + ["start"])[1]
    if mode == "worker": return worker()
    if not os.path.exists(SS):
        if mode == "start": print("Skill safety scan: skillspector is not installed, so new skills "
                                  "were NOT scanned. Review user-added skills manually before use.")
        return
    if mode == "start" and (p := pending()):
        subprocess.Popen([sys.executable, __file__, "worker"], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("Skill safety scan started in the background for: " + ", ".join(p))
    report()
try: main()
except Exception as e: print(f"Skill safety scan error: {e}")
