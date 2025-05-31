#!/usr/bin/env python3
"""
Shutdown script for TutuBot Discord bot.
This script gracefully shuts down the bot by sending a SIGTERM signal.
"""

import os
import signal
import sys
import subprocess
import time

def find_bot_process():
    """Find the bot process by looking for main.py."""
    try:
        # Use ps command to find processes running main.py
        result = subprocess.run(
            ["ps", "aux"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        for line in result.stdout.split('\n'):
            if 'main.py' in line and 'python' in line:
                # Extract PID (second column in ps aux output)
                parts = line.split()
                if len(parts) > 1:
                    try:
                        pid = int(parts[1])
                        return pid
                    except ValueError:
                        continue
        return None
    except subprocess.CalledProcessError:
        return None

def shutdown_bot():
    """Shutdown the bot gracefully."""
    print("Looking for TutuBot process...")
    
    pid = find_bot_process()
    
    if pid is None:
        print("No TutuBot process found.")
        return
    
    print(f"Found TutuBot process with PID: {pid}")
    
    try:
        # Send SIGTERM for graceful shutdown
        print("Sending shutdown signal...")
        os.kill(pid, signal.SIGTERM)
        
        # Wait a moment for graceful shutdown
        time.sleep(2)
        
        # Check if process is still running
        try:
            os.kill(pid, 0)  # This doesn't kill, just checks if process exists
            print("Process still running, sending SIGKILL...")
            os.kill(pid, signal.SIGKILL)
            print("Bot forcefully terminated.")
        except ProcessLookupError:
            print("Bot shutdown successfully.")
            
    except ProcessLookupError:
        print("Process not found (may have already exited).")
    except PermissionError:
        print("Permission denied. You may need to run this script with appropriate permissions.")
    except Exception as e:
        print(f"Error shutting down bot: {e}")

if __name__ == "__main__":
    shutdown_bot()
