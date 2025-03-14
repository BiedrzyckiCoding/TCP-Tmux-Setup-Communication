import discord
import asyncio
import socket

TOKEN = "token"  # Replace with your bot token
CHANNEL_ID = 123445534343242  # Replace with your Discord channel ID
TCP_IP = "127.0.0.1"
TCP_PORT = 5005

intents = discord.Intents.default()
client = discord.Client(intents=intents)

async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """
    Handle each connected TCP client in its own coroutine.
    This is where we parse the inbound messages and forward them to Discord.
    """
    addr = writer.get_extra_info('peername')
    print(f"[DEBUG] New TCP client connected from {addr}")

    # Send a debug message to Discord about the new connection
    channel = client.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(f"[DEBUG] **New TCP client connected** from {addr}")
    else:
        print("[ERROR] Discord channel not found for new client notification.")

    while True:
        try:
            data = await reader.read(1024)
        except ConnectionResetError:
            print(f"[ERROR] Connection reset by {addr}")
            if channel:
                await channel.send(f"[ERROR] **Connection reset** by {addr}")
            break

        if not data:
            print(f"[DEBUG] Client {addr} has disconnected.")
            if channel:
                await channel.send(f"[DEBUG] **Client disconnected**: {addr}")
            break

        # Decode the message
        message = data.decode()

        # Immediately show we got something from this client
        print(f"[DEBUG] got something through tcp from {addr}:\n{message}")

        # Also send a debug message to Discord
        if channel:
            await channel.send(
                f"[DEBUG] **Got something through TCP** from {addr}:\n```{message}```"
            )
        else:
            print("[ERROR] Discord channel not found for debug message.")
 # Parse the message (assuming the same format as the original messages)
        lines = message.split("\n")
        if len(lines) < 2:
            print("[ERROR] Received malformed message, ignoring.")
            if channel:
                await channel.send("[ERROR] Received malformed message, ignoring.")
            continue

        # Typically: first line is "number of restarted minecraft clients: X"
        # second line is "restarted session names:"
        # subsequent lines are the actual session names
        try:
            restart_count_line = lines[0]  # e.g. "number of restarted minecraft clients: 2"
            restart_count = restart_count_line.split(": ")[1]
        except (IndexError, ValueError):
            print("[ERROR] Unable to parse restart count.")
            if channel:
                await channel.send("[ERROR] Unable to parse restart count.")
            continue

        session_names = "\n".join(lines[2:])

        # Format the final Discord message
        discord_message = (
            f"🔄 **Minecraft Clients Restarted: {restart_count}**\n"
            f"🖥 **Sessions:**\n```{session_names}```"
        )

        # Send the formatted restart report to Discord
        if channel:
            print("[DEBUG] Sending formatted restart report to Discord...")
            await channel.send(discord_message)
        else:
            print("[ERROR] Discord channel not found for restart report.")

    # Once we exit the loop, the client is disconnected or errored
    writer.close()
    await writer.wait_closed()
    print(f"[DEBUG] Closed connection with {addr}")
async def start_tcp_server():
    """
    Asynchronously start a TCP server and handle multiple clients in parallel.
    """
    print(f"[DEBUG] Starting TCP server on {TCP_IP}:{TCP_PORT}...")
    server = await asyncio.start_server(handle_client, TCP_IP, TCP_PORT)

    async with server:
        print("[DEBUG] TCP Server is running and ready to accept connections.")
        await server.serve_forever()

@client.event
async def on_ready():
    print(f"[DEBUG] Logged in as {client.user}")

    # Send a startup message to Discord
    channel = client.get_channel(CHANNEL_ID)
    if channel:
        print(f"[DEBUG] Sending startup message to Discord channel {CHANNEL_ID}...")
        await channel.send("✅ **Bot is now online and listening for TCP connections!**")
    else:
        print("[ERROR] Could not send startup message: Channel not found.")

    # Start the TCP server in the background
    client.loop.create_task(start_tcp_server())

client.run(TOKEN)