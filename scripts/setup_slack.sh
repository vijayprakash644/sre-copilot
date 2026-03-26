#!/bin/bash
# Slack app setup helper
# Prints the manifest and required steps to create a Slack app for SRE Copilot.

set -euo pipefail

BASE_URL=${SRE_COPILOT_URL:-https://your-deployment.railway.app}

cat <<'EOF'
╔══════════════════════════════════════════════════════════════╗
║            SRE Copilot — Slack App Setup Guide              ║
╚══════════════════════════════════════════════════════════════╝

Step 1: Create a new Slack app
  → Go to https://api.slack.com/apps
  → Click "Create New App" → "From manifest"
  → Paste the manifest below

Step 2: Install to your workspace
  → In the app settings, click "Install to Workspace"
  → Authorize the requested permissions

Step 3: Copy credentials to .env
  → Bot Token (xoxb-...): SLACK_BOT_TOKEN
  → Signing Secret: SLACK_SIGNING_SECRET
  → App-Level Token (xapp-...): SLACK_APP_TOKEN (only for Socket Mode)

Step 4: Set the Request URL for interactivity
  → Go to "Interactivity & Shortcuts"
  → Set Request URL to: $BASE_URL/slack/events

Step 5: Add the slash command
  → Go to "Slash Commands" → Create New Command
  → Command: /sre-ask
  → Request URL: $BASE_URL/slack/events
  → Short Description: Ask SRE Copilot a question

EOF

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Slack App Manifest (copy this):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cat <<MANIFEST
display_information:
  name: SRE Copilot
  description: AI-powered incident triage assistant
  background_color: "#1a1a2e"

features:
  bot_user:
    display_name: SRE Copilot
    always_online: true
  slash_commands:
    - command: /sre-ask
      url: ${BASE_URL}/slack/events
      description: Ask SRE Copilot a follow-up question about an incident
      usage_hint: "[your question about the incident]"
      should_escape: false

oauth_config:
  scopes:
    bot:
      - chat:write
      - chat:write.public
      - commands
      - channels:read
      - channels:history

settings:
  interactivity:
    is_enabled: true
    request_url: ${BASE_URL}/slack/events
  org_deploy_enabled: false
  socket_mode_enabled: false
  token_rotation_enabled: false
MANIFEST

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "After setup, add to your .env:"
echo "  SLACK_BOT_TOKEN=xoxb-..."
echo "  SLACK_SIGNING_SECRET=..."
echo "  INCIDENTS_CHANNEL=#incidents"
