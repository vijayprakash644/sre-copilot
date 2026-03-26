"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ExternalLink, Copy, CheckCircle2 } from "lucide-react";

interface HealthStatus {
  status: string;
  mode: string;
}

const MODE_DESCRIPTIONS: Record<string, string> = {
  api: "Anthropic API — logs scrubbed before sending. 7-day data retention.",
  bedrock: "AWS Bedrock — data never leaves your AWS account.",
  ollama: "Self-hosted Ollama — fully local, no external calls.",
};

export default function SettingsPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/proxy/health")
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => null);
  }, []);

  const mode = health?.mode ?? "unknown";

  const webhookBase =
    typeof window !== "undefined"
      ? window.location.origin.replace(":3000", ":8000")
      : "https://your-deployment.example.com";

  function copyToClipboard(text: string, id: string) {
    navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  }

  return (
    <div className="p-8 max-w-3xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white mb-1">Settings</h1>
        <p className="text-slate-400 text-sm">
          Workspace configuration. Edit values in your{" "}
          <code className="text-slate-300 bg-slate-700 px-1 rounded text-xs">.env</code>{" "}
          file and restart the backend to apply changes.
        </p>
      </div>

      {/* Deployment mode */}
      <Card className="bg-slate-800 border-slate-700 mb-6">
        <CardHeader className="pb-3">
          <CardTitle className="text-white text-base">Deployment Mode</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3 mb-2">
            <Badge
              className={
                mode === "api"
                  ? "bg-blue-500/20 text-blue-400 border-blue-500/30"
                  : mode === "bedrock"
                  ? "bg-orange-500/20 text-orange-400 border-orange-500/30"
                  : "bg-green-500/20 text-green-400 border-green-500/30"
              }
            >
              {mode}
            </Badge>
          </div>
          <p className="text-slate-400 text-sm">
            {MODE_DESCRIPTIONS[mode] ?? "Unknown mode"}
          </p>
          <p className="text-slate-500 text-xs mt-2">
            Change via{" "}
            <code className="text-slate-400 bg-slate-700 px-1 rounded">
              DEPLOYMENT_MODE
            </code>{" "}
            env var (api | bedrock | ollama)
          </p>
        </CardContent>
      </Card>

      {/* Webhook URLs */}
      <Card className="bg-slate-800 border-slate-700 mb-6">
        <CardHeader className="pb-3">
          <CardTitle className="text-white text-base">Webhook URLs</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {[
            {
              id: "pd",
              label: "PagerDuty",
              url: `${webhookBase}/webhooks/pagerduty`,
              hint: "Set as Webhook URL in PagerDuty → Integrations → Generic Webhooks (v3)",
            },
            {
              id: "am",
              label: "Prometheus AlertManager",
              url: `${webhookBase}/webhooks/alertmanager`,
              hint: "Add to alertmanager.yml under receivers → webhook_configs → url",
            },
            {
              id: "dd",
              label: "Datadog",
              url: `${webhookBase}/webhooks/datadog`,
              hint: "Add in Datadog → Integrations → Webhooks",
            },
          ].map(({ id, label, url, hint }) => (
            <div key={id}>
              <p className="text-white text-sm font-medium mb-1">{label}</p>
              <div className="flex items-center gap-2">
                <code className="text-slate-300 bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs flex-1 overflow-x-auto">
                  {url}
                </code>
                <button
                  className="text-slate-400 hover:text-white transition-colors"
                  onClick={() => copyToClipboard(url, id)}
                  title="Copy"
                >
                  {copied === id ? (
                    <CheckCircle2 className="w-4 h-4 text-green-400" />
                  ) : (
                    <Copy className="w-4 h-4" />
                  )}
                </button>
              </div>
              <p className="text-slate-500 text-xs mt-1">{hint}</p>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Slack */}
      <Card className="bg-slate-800 border-slate-700 mb-6">
        <CardHeader className="pb-3">
          <CardTitle className="text-white text-base">Slack</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-400">Incidents channel</span>
              <code className="text-slate-300 bg-slate-900 px-2 py-0.5 rounded text-xs">
                INCIDENTS_CHANNEL
              </code>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Bot token</span>
              <code className="text-slate-300 bg-slate-900 px-2 py-0.5 rounded text-xs">
                SLACK_BOT_TOKEN
              </code>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Signing secret</span>
              <code className="text-slate-300 bg-slate-900 px-2 py-0.5 rounded text-xs">
                SLACK_SIGNING_SECRET
              </code>
            </div>
          </div>
          <p className="text-slate-500 text-xs mt-3">
            Run{" "}
            <code className="text-slate-400 bg-slate-700 px-1 rounded">
              ./scripts/setup_slack.sh
            </code>{" "}
            for the Slack app manifest and setup instructions.
          </p>
        </CardContent>
      </Card>

      {/* Links */}
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader className="pb-3">
          <CardTitle className="text-white text-base">Resources</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {[
              { label: "Setup guide", href: "/docs/setup-guide" },
              { label: "Deployment modes", href: "/docs/deployment-modes" },
              { label: "Privacy & security", href: "/docs/privacy-security" },
              { label: "API reference", href: "/docs/api-reference" },
            ].map(({ label, href }) => (
              <a
                key={href}
                href={href}
                className="flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                {label}
              </a>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
