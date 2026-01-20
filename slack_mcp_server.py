import os
from typing import Any, Literal
import httpx
from mcp.server.fastmcp import FastMCP
import re

SLACK_API_BASE = "https://slack.com/api"
MCP_TRANSPORT = os.environ.get("MCP_TRANSPORT", "stdio")
LOGS_CHANNEL_ID = os.environ["LOGS_CHANNEL_ID"]

mcp = FastMCP(
    "slack", settings={"host": "127.0.0.1" if MCP_TRANSPORT == "stdio" else "0.0.0.0"}
)


async def make_request(
    url: str, method: str = "POST", payload: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    if MCP_TRANSPORT == "stdio":
        xoxc_token = os.environ["SLACK_XOXC_TOKEN"]
        xoxd_token = os.environ["SLACK_XOXD_TOKEN"]
        user_agent = "MCP-Server/1.0"
    else:
        request_headers = mcp.get_context().request_context.request.headers
        xoxc_token = request_headers["X-Slack-Web-Token"]
        xoxd_token = request_headers["X-Slack-Cookie-Token"]
        user_agent = request_headers.get("User-Agent", "MCP-Server/1.0")

    headers = {
        "Authorization": f"Bearer {xoxc_token}",
        "Content-Type": "application/json",
        "User-Agent": user_agent,
    }

    cookies = {"d": xoxd_token}

    async with httpx.AsyncClient() as client:
        try:
            if method.upper() == "GET":
                response = await client.request(
                    method,
                    url,
                    headers=headers,
                    cookies=cookies,
                    params=payload,
                    timeout=30.0,
                )
            else:
                response = await client.request(
                    method,
                    url,
                    headers=headers,
                    cookies=cookies,
                    json=payload,
                    timeout=30.0,
                )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(e)
            return None


async def log_to_slack(message: str):
    await post_message(LOGS_CHANNEL_ID, message, skip_log=True)


# Validate and convert thread_ts if needed
def convert_thread_ts(ts: str) -> str:
    # If ts is already in the correct format, return as is
    if re.match(r"^\d+\.\d+$", ts):
        return ts
    # If ts is a long integer string (from Slack URL), convert it
    if re.match(r"^\d{16}$", ts):
        return f"{ts[:10]}.{ts[10:]}"
    return ""


@mcp.tool()
async def get_channel_history(channel_id: str) -> list[dict[str, Any]]:
    """Get the history of a channel."""
    await log_to_slack(f"Getting history of channel <#{channel_id}>")
    url = f"{SLACK_API_BASE}/conversations.history"
    payload = {"channel": channel_id}
    data = await make_request(url, payload=payload)
    if data and data.get("ok"):
        return data.get("messages", [])
    return []


@mcp.tool()
async def post_message(
    channel_id: str, message: str, thread_ts: str = "", skip_log: bool = False
) -> bool:
    """Post a message to a channel."""
    if not skip_log:
        await log_to_slack(f"Posting message to channel <#{channel_id}>: {message}")
    await join_channel(channel_id, skip_log=skip_log)
    url = f"{SLACK_API_BASE}/chat.postMessage"
    payload = {"channel": channel_id, "text": message}
    if thread_ts:
        payload["thread_ts"] = convert_thread_ts(thread_ts)
    data = await make_request(url, payload=payload)
    return data.get("ok") if data else False


@mcp.tool()
async def post_command(
    channel_id: str, command: str, text: str, skip_log: bool = False
) -> bool:
    """Post a command to a channel."""
    if not skip_log:
        await log_to_slack(
            f"Posting command to channel <#{channel_id}>: {command} {text}"
        )
    await join_channel(channel_id, skip_log=skip_log)
    url = f"{SLACK_API_BASE}/chat.command"
    payload = {"channel": channel_id, "command": command, "text": text}
    data = await make_request(url, payload=payload)
    return data.get("ok") if data else False


@mcp.tool()
async def add_reaction(channel_id: str, message_ts: str, reaction: str) -> bool:
    """Add a reaction to a message."""
    await log_to_slack(
        f"Adding reaction to message {message_ts} in channel <#{channel_id}>: :{reaction}:"
    )
    url = f"{SLACK_API_BASE}/reactions.add"
    payload = {
        "channel": channel_id,
        "name": reaction,
        "timestamp": convert_thread_ts(message_ts),
    }
    data = await make_request(url, payload=payload)
    return data.get("ok") if data else False


@mcp.tool()
async def whoami() -> str:
    """Checks authentication & identity."""
    await log_to_slack("Checking authentication & identity")
    url = f"{SLACK_API_BASE}/auth.test"
    data = await make_request(url)
    return data.get("user") if data else ""


@mcp.tool()
async def join_channel(channel_id: str, skip_log: bool = False) -> bool:
    """Join a channel."""
    if not skip_log:
        await log_to_slack(f"Joining channel <#{channel_id}>")
    url = f"{SLACK_API_BASE}/conversations.join"
    payload = {"channel": channel_id}
    data = await make_request(url, payload=payload)
    return data.get("ok") if data else False


@mcp.tool()
async def send_dm(user_id: str, message: str) -> bool:
    """Send a direct message to a user."""
    await log_to_slack(f"Sending direct message to user <@{user_id}>: {message}")
    url = f"{SLACK_API_BASE}/conversations.open"
    payload = {"users": user_id, "return_dm": True}
    data = await make_request(url, payload=payload)
    if data and data.get("ok"):
        return await post_message(data.get("channel").get("id"), message)
    return False


@mcp.tool()
async def search_messages(
    query: str, sort: Literal["timestamp", "score"] = "timestamp", count: int = 20
) -> list[dict[str, Any]]:
    """Search for messages in the workspace.
    
    Args:
        query: Search query. Supports Slack syntax:
            - 'in:channel-name' - search in a channel
            - 'in:<@UserID>' - search DMs with a specific user (e.g., 'in:<@UG7BN3XAS>')
            - 'is:dm' - all direct messages
            - 'after:2026-01-05' - date filters
        sort: Sort by 'timestamp' or 'score'
        count: Number of messages to return (max 100, default 20)
    """
    # Slack API max is 100
    count = min(count, 100)
    await log_to_slack(f"Searching for messages: {query} (limit: {count})")
    url = f"{SLACK_API_BASE}/search.messages"
    payload = {"query": query, "sort": sort, "count": count}
    data = await make_request(url, method="GET", payload=payload)
    if data and data.get("ok"):
        return data.get("messages", {}).get("matches", [])
    return []


@mcp.tool()
async def search_files(
    query: str, user: str = "", after: str = "", count: int = 20
) -> list[dict[str, Any]]:
    """Search for files and documents in the workspace.
    
    Args:
        query: Search query (document title, keywords)
        user: Optional - filter by username who shared the file
        after: Optional date filter (e.g., "2026-01-05")
        count: Number of files to return (max 100, default 20)
    
    Returns:
        List of files with titles, links, and metadata
    """
    # Build search query
    search_query = query
    if user:
        search_query += f" from:{user}"
    if after:
        search_query += f" after:{after}"
    
    count = min(count, 100)
    await log_to_slack(f"Searching files: {search_query} (limit: {count})")
    
    url = f"{SLACK_API_BASE}/search.files"
    payload = {"query": search_query, "sort": "timestamp", "count": count}
    data = await make_request(url, method="GET", payload=payload)
    
    if data and data.get("ok"):
        return data.get("files", {}).get("matches", [])
    return []


@mcp.tool()
async def search_dms(
    user_id: str, query: str = "", after: str = "", count: int = 20
) -> list[dict[str, Any]]:
    """Search direct messages with a specific user.
    
    Args:
        user_id: Slack user ID (e.g., "UG7BN3XAS") - find this from user's Slack profile
        query: Optional search terms to filter messages
        after: Optional date filter (e.g., "2026-01-05")
        count: Number of messages to return (max 100, default 20)
    
    Returns:
        List of messages from the DM conversation
    """
    await log_to_slack(f"Searching DMs with user <@{user_id}>")
    
    # Search in DMs with this user
    dm_query = f"in:<@{user_id}>"
    if query:
        dm_query += f" {query}"
    if after:
        dm_query += f" after:{after}"
    
    return await search_messages(dm_query, "timestamp", count)
    
@mcp.tool()
async def get_thread_by_link(thread_link: str, limit: int = 200) -> dict[str, Any]:
    """Get a full thread by providing a Slack thread link.
    
    Args:
        thread_link: A Slack thread URL
        limit: Maximum number of messages to return (default 200)
    
    Returns:
        A dict with 'thread_starter' (the original message) and 'replies' (all thread messages)
    """
    await log_to_slack(f"Fetching thread from link: {thread_link}")
    
    # Parse the URL to extract channel_id and timestamps
    # Format: https://workspace.slack.com/archives/CHANNEL_ID/pTIMESTAMP(?thread_ts=PARENT_TS)
    
    # Extract channel_id
    channel_match = re.search(r'/archives/([A-Z0-9]+)/', thread_link)
    if not channel_match:
        return {"error": "Could not extract channel ID from link", "thread_starter": None, "replies": []}
    
    channel_id = channel_match.group(1)
    
    # Extract message timestamp from the 'p' value
    ts_match = re.search(r'/p(\d+)', thread_link)
    if not ts_match:
        return {"error": "Could not extract message timestamp from link", "thread_starter": None, "replies": []}
    
    message_ts_raw = ts_match.group(1)
    
    # Check if there's a thread_ts query parameter (meaning this is a reply, not the thread starter)
    thread_ts_match = re.search(r'thread_ts=(\d+\.\d+)', thread_link)
    
    if thread_ts_match:
        # This is a link to a reply - use the thread_ts as the parent
        thread_ts = thread_ts_match.group(1)
    else:
        # This is a direct link to the thread starter - convert the p-value to timestamp
        thread_ts = convert_thread_ts(message_ts_raw)
    
    if not thread_ts:
        return {"error": "Could not determine thread timestamp", "thread_starter": None, "replies": []}
    
    # Fetch all replies in the thread (GET with query params per Slack API docs)
    replies_url = f"{SLACK_API_BASE}/conversations.replies"
    replies_payload = {
        "channel": channel_id,
        "ts": thread_ts,
        "limit": limit,
    }
    replies_data = await make_request(replies_url, method="GET", payload=replies_payload)
    
    if not replies_data or not replies_data.get("ok"):
        error_msg = replies_data.get("error", "Unknown error") if replies_data else "Request failed"
        return {
            "error": f"Failed to fetch thread: {error_msg}",
            "debug": {
                "channel_id": channel_id,
                "thread_ts": thread_ts,
                "message_ts_raw": message_ts_raw,
                "had_thread_ts_in_url": thread_ts_match is not None,
                "api_payload": replies_payload,
                "api_response": replies_data,
            },
            "thread_starter": None,
            "replies": []
        }
    
    messages = replies_data.get("messages", [])
    
    return {
        "channel_id": channel_id,
        "thread_ts": thread_ts,
        "thread_starter": messages[0] if messages else None,
        "replies": messages[1:] if len(messages) > 1 else [],
        "total_messages": len(messages),
    }


@mcp.tool()
async def get_thread_by_text(
    channel_name: str, message_text: str, limit: int = 200
) -> dict[str, Any]:
    """Find a thread by searching for message text and return all replies.
    
    Args:
        channel_name: The channel name to search in (e.g., "general" or "forum-llama-stack-core")
        message_text: Part of or full text from the first message in the thread
        limit: Maximum number of messages to return (default 200)
    
    Returns:
        A dict with 'thread_starter' (the original message) and 'replies' (all thread messages)
    """
    await log_to_slack(
        f"Searching for thread in #{channel_name} containing: {message_text[:50]}..."
    )
    
    # Step 1: Search for the message in the channel
    search_url = f"{SLACK_API_BASE}/search.messages"
    search_payload = {"query": f"in:{channel_name} {message_text}", "sort": "timestamp"}
    search_data = await make_request(search_url, method="GET", payload=search_payload)
    
    if not search_data or not search_data.get("ok"):
        return {"error": "Search failed", "thread_starter": None, "replies": []}
    
    matches = search_data.get("messages", {}).get("matches", [])
    if not matches:
        return {"error": "No messages found matching the text", "thread_starter": None, "replies": []}
    
    # Step 2: Find the thread_ts and channel_id from the search result
    message = matches[0]
    thread_ts = message.get("thread_ts") or message.get("ts")
    channel_id = message.get("channel", {}).get("id")
    
    if not thread_ts:
        return {"error": "Could not determine thread timestamp", "thread_starter": None, "replies": []}
    
    if not channel_id:
        return {"error": "Could not determine channel ID", "thread_starter": None, "replies": []}
    
    # Step 3: Fetch all replies in the thread
    replies_url = f"{SLACK_API_BASE}/conversations.replies"
    replies_payload = {
        "channel": channel_id,
        "ts": convert_thread_ts(thread_ts),
        "limit": limit,
    }
    replies_data = await make_request(replies_url, payload=replies_payload)
    
    if not replies_data or not replies_data.get("ok"):
        return {"error": "Failed to fetch thread replies", "thread_starter": message, "replies": []}
    
    messages = replies_data.get("messages", [])
    
    return {
        "thread_starter": messages[0] if messages else message,
        "replies": messages[1:] if len(messages) > 1 else [],
        "total_messages": len(messages),
    }


if __name__ == "__main__":
    mcp.run(transport=MCP_TRANSPORT)
