import subprocess
import time
import socket
import os

CHECK_INTERVAL = 1800  # 30 minutes
TCP_IP = "127.0.0.1"
TCP_PORT = 5005
LOG_FILE = "missing_sessions.txt"
MINECRAFT_COMMAND = "./MinecraftClient-20241227-281-linux-x64"
EXCLUDED_SESSION = "client"  # Session name to exclude

def get_tmux_sessions():
    """Retrieve tmux session names and their window names using a Bash snippet."""
    sessions = {}
    print("[DEBUG] Checking tmux sessions...")

    # Run the Bash command to list sessions
    result = subprocess.run(
        ["tmux", "list-sessions", "-F", "#{session_name}"],
        capture_output=True, text=True
    )

    session_list = result.stdout.strip().split("\n")

    if not session_list or session_list == [""]:
        print("[DEBUG] No tmux sessions found.")
        return sessions  # Return empty dict if no sessions found

    # Loop through each session and get windows
    for session in session_list:
        result = subprocess.run(
            ["tmux", "list-windows", "-t", session, "-F", "#{window_name}"],
            capture_output=True, text=True
        )
        windows = result.stdout.strip().split("\n")
        sessions[session] = windows
        print(f"[DEBUG] Found session: {session}, Windows: {windows}")

    return sessions

def read_existing_log():
    """Reads the log file, ensuring proper session names."""
    if not os.path.exists(LOG_FILE):
        return set()

    with open(LOG_FILE, "r") as f:
        return set(f.read().splitlines())
def log_missing_sessions():
    """Check tmux sessions and log missing Minecraft clients, preventing duplicates."""
    sessions = get_tmux_sessions()
    missing_sessions = []

    # Load existing log to avoid duplicate entries
    existing_sessions = read_existing_log()

    for session, windows in sessions.items():
        if session == EXCLUDED_SESSION:
            print(f"[DEBUG] Skipping excluded session: {session}")
            continue  # Skip excluded session

        # Only log if "bash" is in the windows list
        if "bash" in windows and session not in existing_sessions:
            missing_sessions.append(session)
            print(f"[DEBUG] Logging missing session: {session}")

    if missing_sessions:
        with open(LOG_FILE, "a") as f:
            f.writelines("\n".join(missing_sessions) + "\n")

    return missing_sessions
def restart_missing_clients():
    """Restart missing Minecraft clients one by one, waiting 5 minutes between each."""
    if not os.path.exists(LOG_FILE):
        print("[DEBUG] Log file not found, skipping restart.")
        return []

    # Read log file and remove empty lines
    with open(LOG_FILE, "r") as f:
        sessions = [line.strip() for line in f.readlines() if line.strip()]

    if not sessions:
        print("[DEBUG] No valid sessions found in log file.")
        return []

    restarted_sessions = []

    for session in sessions:
        if session == EXCLUDED_SESSION:
            print(f"[DEBUG] Skipping excluded session: {session}")
            continue

        print(f"[DEBUG] Restarting session: {session}")
        command = f'tmux send-keys -t {session} "{MINECRAFT_COMMAND} {session}" C-m'
        subprocess.run(command, shell=True)
        restarted_sessions.append(session)

        print(f"[DEBUG] Started Minecraft client for session: {session}")
        time.sleep(600)  # Wait 5 minutes before starting the next one

                # Remove session from the log file after restarting
        remove_session_from_log(session)

    return restarted_sessions

def remove_session_from_log(session_name):
    """Removes a session name from the log file after it has been restarted."""
    print(f"[DEBUG] Removing restarted session '{session_name}' from log file.")

    with open(LOG_FILE, "r") as f:
        sessions = [
            line.strip() for line in f.readlines()
            if line.strip() and line.strip() != session_name
        ]

    with open(LOG_FILE, "w") as f:
        f.writelines("\n".join(sessions) + "\n")

    print("[DEBUG] Log file updated after removing session.")
def send_tcp_report(restarted_sessions):
    """Send a TCP message to the server with session restart info."""
    if not restarted_sessions:
        print("[DEBUG] No sessions restarted, skipping TCP report.")
        return

    message = f"number of restarted minecraft clients: {len(restarted_sessions)}\n"
    message += "restarted session names:\n"
    message += "\n".join(restarted_sessions)

    print(f"[DEBUG] Sending TCP report to {TCP_IP}:{TCP_PORT}...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((TCP_IP, TCP_PORT))
        s.sendall(message.encode())
    print("[DEBUG] TCP report sent successfully.")

def main():
    while True:
        print("[DEBUG] Starting session check...")
        missing_sessions = log_missing_sessions()
        if missing_sessions:
            restarted_sessions = restart_missing_clients()
            send_tcp_report(restarted_sessions)

        print(f"[DEBUG] Sleeping for {CHECK_INTERVAL} seconds before rechecking...")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    print("[DEBUG] Client script started.")
    main()