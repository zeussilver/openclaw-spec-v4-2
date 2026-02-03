#!/bin/bash
# entrypoint.sh - Sandbox container entrypoint
# Executes the harness with the provided skill path

set -e

if [ -z "$1" ]; then
    echo "Usage: entrypoint.sh <skill_path>"
    exit 1
fi

exec python /sandbox/harness.py "$1"
