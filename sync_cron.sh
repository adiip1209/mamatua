#!/bin/bash
# EvoMap GitHub Sync — runs every hour
# Syncs EvoMap status/metrics to GitHub repo adiip1209/mamatua

cd /home/ubuntu/mamatua
python3 sync_evomap.py 2>&1
