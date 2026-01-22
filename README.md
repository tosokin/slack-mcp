# slack-mcp

A Model Context Protocol (MCP) server that enables AI assistants to interact with Slack workspaces. This server provides a bridge between AI tools and Slack, allowing you to read messages, post content, and manage Slack channels programmatically through MCP-compatible clients.

## What is this and why should I use it?

This MCP server transforms your Slack workspace into an AI-accessible environment. Instead of manually switching between your AI assistant and Slack, you can now:

- **Read channel messages** - Get real-time updates and conversation history
- **Search messages** - Search across channels, DMs, and threads with advanced filtering
- **Read and summarize full threads** - Extract complete thread conversations by text search or by providing a thread link
- **Post messages** - Send messages to channels and reply in threads
- **Search DMs** - Find and read direct message conversations with specific users
- **Find user mentions** - Track when you or colleagues are mentioned across channels
- **Search by topic** - Find discussions about specific topics across your entire workspace
- **Find group conversations** - Locate private group DMs and multi-person conversations
- **Search files** - Find documents and files shared in the workspace

### Key Benefits

- **AI-Assisted Operations**: Let AI read, analyze, and respond to Slack messages on your behalf
- **Enhanced Productivity**: Let AI help summarize conversations and draft responses
- **Team Collaboration**: Enable AI assistants to participate in discussions and provide insights

### Use Cases

- **Team Assistant**: Have an AI that can read team updates and provide summaries
- **Knowledge Base**: AI that can search through channel history and provide context
- **Thread Summarizer**: AI that can read and summarize long Slack threads
- **Message Drafter**: AI that can help compose and post responses to channels

## Configuration

### Step 1: Clone and Set Up the Repository

```bash
# Clone the repository
git clone https://github.com/tosokin/slack-mcp.git
cd slack-mcp

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

After activation, you should see `(venv)` at the beginning of your terminal prompt.

### Step 2: Get Your Slack Tokens

You need two tokens from your Slack web session.

**Open Slack in your browser:**
1. Go to your Slack workspace in Chrome or Firefox (not the desktop app)
2. Make sure you're logged in
3. Press `F12` (or `Cmd+Option+I` on Mac) to open Developer Tools

**Get Token #1: SLACK_XOXD_TOKEN**
1. In Developer Tools, click the **"Application"** tab (Chrome) or **"Storage"** tab (Firefox)
2. In the left sidebar, click **Cookies** → click your Slack workspace URL
3. Find the cookie named **`d`**
4. Copy its **Value** (it starts with `xoxd-`)
5. 📝 Save this somewhere - this is your `SLACK_XOXD_TOKEN`

**Get Token #2: SLACK_XOXC_TOKEN**
1. Stay in Developer Tools, go to the **"Network"** tab
2. In the filter box at the top, type `api` to filter requests
3. In Slack, do any action (e.g., click on a different channel, scroll in a channel)
4. Look for requests like `conversations.history`, `conversations.list`, `client.counts`, etc.
5. Click on one of those requests
6. Click on the **"Payload"** tab
7. Find the field called `token` - it shows `xoxc-...`
8. 📝 Copy this value - this is your `SLACK_XOXC_TOKEN`

### Step 3: Create a Logging Channel

The MCP server logs all tool calls to a Slack channel for auditing and debugging:

1. **Create a logging channel** in Slack (e.g., `#mcp-logs` or `#ai-assistant-logs`)
   - This channel will receive a message every time the AI uses a Slack tool
   - Useful for tracking what actions the AI is performing on your behalf
2. Right-click the channel name → **"Copy link"**
3. The link looks like: `https://yourworkspace.slack.com/archives/C08XXXXXXXX`
4. Copy the `C08XXXXXXXX` part - this is your `LOGS_CHANNEL_ID`

### Step 4: Configure Your MCP Client

Add this to your MCP client configuration file.

**For Cursor** (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "slack": {
      "command": "python",
      "args": ["/path/to/slack-mcp/slack_mcp_server.py"],
      "env": {
        "SLACK_XOXC_TOKEN": "xoxc-your-token-here",
        "SLACK_XOXD_TOKEN": "xoxd-your-token-here",
        "LOGS_CHANNEL_ID": "C08XXXXXXXX"
      }
    }
  }
}
```

**Important**: Replace `/path/to/slack-mcp/` with the actual path where you cloned this repository.

### Step 5: Reload Cursor

After saving your `mcp.json` configuration, reload Cursor for the changes to take effect:
- Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows/Linux)
- Type "Reload Window" and select it

You should now see the Slack MCP server available in your AI assistant.

## Available Tools

This MCP server provides the following tools:

### Message & Thread Operations
- **`get_channel_history`** - Get recent messages from a channel
- **`search_messages`** - Search messages across workspace
- **`search_dms`** - Search direct messages with a specific user
- **`search_user_mentions`** - Search for messages where a user is mentioned
- **`search_files`** - Search for files and documents shared in the workspace
- **`get_thread_by_text`** - Find a thread by searching for message text
- **`get_thread_by_link`** - Fetch a complete thread by providing a Slack thread URL

### Communication
- **`post_message`** - Send messages to channels and reply to threads
- **`post_command`** - Execute Slack slash commands
- **`send_dm`** - Send direct messages to users
- **`add_reaction`** - Add emoji reactions to messages

### Other
- **`join_channel`** - Join a channel
- **`whoami`** - Get the current user's identity


## Example Usage

### Example 1: Search for Recent Discussions

```
User: "Search for messages about 'kubernetes' in the last week"

AI uses: search_messages
- query: "kubernetes after:2026-01-11"
- Returns: List of messages with timestamps, users, and thread links
```

### Example 2: Read a Complete Thread

```
User: "Read the full thread about the deployment issue"

AI uses: get_thread_by_text
- channel_name: "team-engineering"
- message_text: "deployment failed on production"
- Returns: Original message + all replies in the thread
```

### Example 3: Find Mentions of a User

```
User: "Find all mentions of johndoe from last week"

AI uses: search_user_mentions
- username: "johndoe"
- after: "2026-01-15"
- Returns: List of messages where @johndoe was mentioned
```

### Example 4: Find and DM Someone

```
User: "Send a DM to Sarah about the meeting"

Step 1 - AI finds user ID from profile or search
Step 2 - AI uses: send_dm
- user_id: "U0XXXXXXXXX"
- message: "Meeting reminder text..."
```

## Recommended AI Rules

Add these rules to your AI assistant's configuration (e.g., Cursor Settings → Rules for AI) for the best experience with this MCP server:

```markdown
# Slack MCP Protocol

When using Slack MCP tools that return messages:
- mcp_slack_search_messages
- mcp_slack_search_dms
- mcp_slack_search_user_mentions
- mcp_slack_search_files
- mcp_slack_get_channel_history
- mcp_slack_get_thread_by_text
- mcp_slack_get_thread_by_link

1. ALWAYS present search results as a numbered list FIRST before analyzing
2. For each result include:
   - Username and date
   - First 100 characters of message text
   - Thread link (if available)
3. Ask user "Which result should I read?" and wait for response
4. NEVER filter or assume which result is correct
5. NEVER skip showing results and jump straight to analysis
6. Only after user selects a specific result, then read and analyze it

Format:
"I found 5 results:
1. @username (Date) - 'message preview...' → [Thread link]
2. @username (Date) - 'message preview...' → [Thread link]
...
Which one would you like me to read?"

# Slack Permalink Rule

When presenting Slack message links to the user:
- ALWAYS use the exact `permalink` field from the Slack API response
- NEVER modify, truncate, or "clean up" the URL
- If the permalink includes `?thread_ts=...`, keep it exactly as-is
- If the permalink has no query parameters, show it as-is

The API knows when thread_ts is needed. Trust it.
```

## Logging

By default, all MCP tool calls are logged to the channel specified by `LOGS_CHANNEL_ID`. This helps with:
- Debugging issues
- Tracking AI assistant activities
- Auditing workspace interactions

To disable logging for specific sensitive operations, use the `skip_log: true` parameter where available.

