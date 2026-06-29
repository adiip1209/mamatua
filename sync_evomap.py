#!/usr/bin/env python3
"""EvoMap GitHub Sync — syncs status/metrics to adiip1209/mamatua repo"""
import json, os, subprocess
from datetime import datetime, timezone

REPO = "/home/ubuntu/mamatua"
NODE_ID = "node_727ea639c9c7352b"

def run(cmd, cwd=REPO):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)

def sync():
    evomap_dir = os.path.join(REPO, "evomap")
    os.makedirs(evomap_dir, exist_ok=True)
    
    # Copy node_id (public)
    with open(os.path.join(evomap_dir, "node_id"), "w") as f:
        f.write(NODE_ID)
    
    # Fetch live data
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
    rejected = len([a for a in assets if a.get("status") == "rejected"])
    total_reuse = sum(a.get("reuse_count", 0) for a in assets)
    total_views = sum(a.get("view_count", 0) for a in assets)
    pending_subs = len([t for t in tasks if t.get("my_submission_status") == "pending"])
    approved_subs = len([t for t in tasks if t.get("my_submission_status") in ("approved", "bounty_approved")])
    
    status = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "node_id": NODE_ID,
        "credits": hb.get("credit_balance", 0),
        "node_status": hb.get("node_status", "?"),
        "survival_status": hb.get("survival_status", "?"),
        "reputation": hb.get("reputation", "?"),
        "assets": {
            "total": len(assets),
            "promoted": promoted,
            "candidate": candidate,
            "rejected": rejected,
            "total_reuse": total_reuse,
            "total_views": total_views
        },
        "submissions": {
            "total": len(tasks),
            "pending": pending_subs,
            "approved": approved_subs
        },
        "top_assets": sorted(
            [{"gdi": a.get("gdi_score",0), "type": a.get("asset_type"), "title": a.get("short_title",""), "reuse": a.get("reuse_count",0)} for a in assets if a.get("status")=="promoted"],
            key=lambda x: x["gdi"], reverse=True
        )[:15]
    }
    
    with open(os.path.join(evomap_dir, "status.json"), "w") as f:
        json.dump(status, f, indent=2)
    
    # Save assets list
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
    
    # Save tasks
    with open(os.path.join(evomap_dir, "tasks.json"), "w") as f:
        json.dump([{
            "task_id": t.get("task_id"),
            "title": t.get("title", "")[:100],
            "status": t.get("my_submission_status", "?")
        } for t in tasks], f, indent=2)
    
    # Git commit and push
    run("git add -A")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    result = run(f'git commit -m "evomap sync {ts} — credits: {status["credits"]}, promoted: {promoted}, pending: {pending_subs}"')
    if "nothing to commit" in result.stdout:
        print("No changes to sync")
        return
    
    push_result = run("git push origin main 2>&1")
    if push_result.returncode == 0:
        print(f"Synced! Credits: {status['credits']} | Promoted: {promoted} | Pending: {pending_subs}")
    else:
        # Try SSH
        run("git remote set-url origin git@github.com-adib:adiip1209/mamatua.git")
        push2 = run("git push origin main 2>&1")
        if push2.returncode == 0:
            print(f"Synced via SSH! Credits: {status['credits']} | Promoted: {promoted}")
        else:
            print(f"Push failed: {push2.stderr[:200]}")

if __name__ == "__main__":
    sync()
