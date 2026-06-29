#!/usr/bin/env python3
"""EvoMap GitHub Sync — syncs status/metrics to adiip1209/mamatua repo"""
import json, os, shutil, subprocess
from datetime import datetime, timezone

REPO = "/home/ubuntu/mamatua"
NODE_ID = "node_727ea639c9c7352b"

def run(cmd, cwd=REPO):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)

def sync():
    evomap_dir = os.path.join(REPO, "evomap")
    os.makedirs(evomap_dir, exist_ok=True)
    
    # 1. Copy node_id (public, safe)
    shutil.copy2("/home/ubuntu/.evomap/node_id", os.path.join(evomap_dir, "node_id"))
    
    # 2. Generate status report
    import urllib.request
    secret = open("/home/ubuntu/.evomap/node_secret").read().strip()
    
    # Heartbeat
    req = urllib.request.Request("https://evomap.ai/a2a/heartbeat",
        data=json.dumps({"node_id": NODE_ID}).encode(), method="POST",
        headers={"Authorization": "Bearer " + secret, "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    hb = json.loads(urllib.request.urlopen(req, timeout=20).read())
    
    # Assets
    req2 = urllib.request.Request(f"https://evomap.ai/a2a/assets/published-by-me?node_id={NODE_ID}&limit=200&status=all", method="GET",
        headers={"Authorization": "Bearer " + secret, "User-Agent": "Mozilla/5.0"})
    assets = json.loads(urllib.request.urlopen(req2, timeout=20).read()).get("assets", [])
    
    # Tasks
    req3 = urllib.request.Request(f"https://evomap.ai/a2a/task/my?node_id={NODE_ID}", method="GET",
        headers={"Authorization": "Bearer " + secret, "User-Agent": "Mozilla/5.0"})
    tasks = json.loads(urllib.request.urlopen(req3, timeout=20).read()).get("tasks", [])
    
    # Build status
    promoted = len([a for a in assets if a.get("status") == "promoted"])
    candidate = len([a for a in assets if a.get("status") == "candidate"])
    total_reuse = sum(a.get("reuse_count", 0) for a in assets)
    total_views = sum(a.get("view_count", 0) for a in assets)
    
    pending_subs = len([t for t in tasks if t.get("my_submission_status") == "pending"])
    
    status = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "node_id": NODE_ID,
        "credits": hb.get("credit_balance", 0),
        "node_status": hb.get("node_status", "?"),
        "assets": {
            "total": len(assets),
            "promoted": promoted,
            "candidate": candidate,
            "total_reuse": total_reuse,
            "total_views": total_views
        },
        "submissions": {
            "total": len(tasks),
            "pending": pending_subs
        },
        "top_assets": sorted(
            [{"gdi": a.get("gdi_score",0), "type": a.get("asset_type"), "title": a.get("short_title","")} for a in assets if a.get("status")=="promoted"],
            key=lambda x: x["gdi"], reverse=True
        )[:10]
    }
    
    with open(os.path.join(evomap_dir, "status.json"), "w") as f:
        json.dump(status, f, indent=2)
    
    # 3. Save full assets list (without secrets)
    with open(os.path.join(evomap_dir, "assets.json"), "w") as f:
        json.dump([{
            "asset_id": a.get("asset_id"),
            "type": a.get("asset_type"),
            "status": a.get("status"),
            "gdi": a.get("gdi_score", 0),
            "reuse": a.get("reuse_count", 0),
            "views": a.get("view_count", 0),
            "title": a.get("short_title", "")
        } for a in assets], f, indent=2)
    
    # 4. Save task submissions
    with open(os.path.join(evomap_dir, "tasks.json"), "w") as f:
        json.dump([{
            "task_id": t.get("task_id"),
            "title": t.get("title", "")[:100],
            "status": t.get("my_submission_status", "?")
        } for t in tasks], f, indent=2)
    
    # 5. Git commit and push
    run("git add -A")
    result = run(f'git commit -m "evomap sync {datetime.now().strftime("%Y-%m-%d %H:%M")} — credits: {status["credits"]}, promoted: {promoted}"')
    if "nothing to commit" in result.stdout:
        print("No changes to sync")
        return
    
    push_result = run("git push origin main 2>&1 || git push origin master 2>&1")
    if push_result.returncode == 0:
        print(f"Synced! Credits: {status['credits']} | Promoted: {promoted} | Pending: {pending_subs}")
    else:
        print(f"Push failed: {push_result.stderr[:200]}")

if __name__ == "__main__":
    sync()
