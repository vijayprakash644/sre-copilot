import Link from "next/link";
import {
  Zap,
  BookOpen,
  Shield,
  BarChart3,
  GitBranch,
  Bell,
  CheckCircle2,
  ArrowRight,
  ChevronDown,
  Terminal,
  Layers,
  Clock,
} from "lucide-react";
import { SlackMockup } from "@/components/landing/slack-mockup";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

// ── Stat bar data ──────────────────────────────────────────────────────────────
const stats = [
  { value: "< 10 sec", label: "to diagnosis" },
  { value: "89%", label: "avg MTTR reduction" },
  { value: "4", label: "deployment modes" },
  { value: "24/7", label: "autonomous monitoring" },
];

// ── How it works ───────────────────────────────────────────────────────────────
const steps = [
  {
    number: "01",
    icon: <Bell className="w-6 h-6" />,
    title: "Alert fires",
    description:
      "A PagerDuty, Grafana, or custom webhook fires. SRE Copilot receives the raw payload within milliseconds.",
  },
  {
    number: "02",
    icon: <Zap className="w-6 h-6" />,
    title: "AI diagnoses",
    description:
      "Our LLM cross-references your runbooks, recent deploys, and live metrics to pinpoint the root cause with confidence scoring.",
  },
  {
    number: "03",
    icon: <CheckCircle2 className="w-6 h-6" />,
    title: "Actionable response",
    description:
      "Numbered remediation steps posted to Slack, Teams, or your ticket system — ready for a human or automated executor.",
  },
];

// ── Features ───────────────────────────────────────────────────────────────────
const features = [
  {
    icon: <BookOpen className="w-5 h-5 text-blue-400" />,
    title: "Runbook-aware RAG",
    description:
      "Upload PDFs, Markdown, or Confluence exports. Every diagnosis cites the exact runbook section it used.",
  },
  {
    icon: <GitBranch className="w-5 h-5 text-violet-400" />,
    title: "Deploy correlation",
    description:
      "Automatically correlates incidents with recent deployments from GitHub, Argo, or Spinnaker within the blast radius.",
  },
  {
    icon: <Shield className="w-5 h-5 text-green-400" />,
    title: "Confidence scoring",
    description:
      "Every diagnosis ships with a 0–100% confidence score and explicit reasoning. Never blindly trust an AI again.",
  },
  {
    icon: <BarChart3 className="w-5 h-5 text-orange-400" />,
    title: "MTTR analytics",
    description:
      "Track diagnosis accuracy, MTTR trends, and cost-of-downtime dashboards. Prove ROI in your next review.",
  },
  {
    icon: <Layers className="w-5 h-5 text-pink-400" />,
    title: "4 deployment modes",
    description:
      "API only, Slack bot, Slack webhook, or full hybrid. Deploy in your VPC or use our managed cloud. Your choice.",
  },
  {
    icon: <Terminal className="w-5 h-5 text-cyan-400" />,
    title: "Feedback loop",
    description:
      "Engineers rate every diagnosis. The model fine-tunes on your infrastructure patterns over time.",
  },
];

// ── Pricing ────────────────────────────────────────────────────────────────────
const plans = [
  {
    name: "Free",
    price: "$0",
    period: "/month",
    description: "For solo SREs and hobbyists",
    features: [
      "100 diagnoses / month",
      "1 runbook upload",
      "API access",
      "Community support",
    ],
    cta: "Get started",
    highlighted: false,
  },
  {
    name: "Team",
    price: "$200",
    period: "/month",
    description: "For growing on-call teams",
    features: [
      "Unlimited diagnoses",
      "Unlimited runbooks",
      "Slack bot + webhook",
      "Deploy correlation",
      "MTTR analytics",
      "Priority support (24h SLA)",
    ],
    cta: "Start free trial",
    highlighted: true,
  },
  {
    name: "Enterprise",
    price: "$500",
    period: "/month",
    description: "For large engineering orgs",
    features: [
      "Everything in Team",
      "VPC / self-hosted deploy",
      "Custom LLM fine-tuning",
      "SSO / SAML",
      "Audit logs",
      "Dedicated SRE success manager",
      "99.9% SLA",
    ],
    cta: "Contact sales",
    highlighted: false,
  },
];

// ── FAQ ────────────────────────────────────────────────────────────────────────
const faqs = [
  {
    q: "What alert sources do you support?",
    a: "SRE Copilot accepts any JSON webhook payload. Native integrations exist for PagerDuty, Grafana, Prometheus AlertManager, Datadog, and OpsGenie. Custom mappings take ~5 minutes.",
  },
  {
    q: "Does my data leave my infrastructure?",
    a: "On the Enterprise plan you can deploy fully within your VPC using our Docker image. Alert payloads and runbooks never leave your environment.",
  },
  {
    q: "Which LLMs does SRE Copilot use?",
    a: "We default to GPT-4o with fallback to Claude 3.5 Sonnet for long-context runbooks. Enterprise customers can bring their own API keys or point to a local Ollama instance.",
  },
  {
    q: "How long does onboarding take?",
    a: "Most teams are fully operational in under 30 minutes. Upload your runbooks, point your alerting tool webhook, and add the Slack app.",
  },
  {
    q: "What happens when the AI is wrong?",
    a: "Engineers click 'Incorrect' on the Slack response, add context, and the feedback is captured. Confidence scores tell you when to trust the diagnosis more carefully.",
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#0a0b0f] text-white">
      {/* ── Navigation ── */}
      <nav className="fixed top-0 left-0 right-0 z-50 border-b border-white/5 bg-[#0a0b0f]/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-violet-600 flex items-center justify-center">
                <Zap className="w-4 h-4 text-white" />
              </div>
              <span className="font-bold text-white text-lg">SRE Copilot</span>
            </div>
            <div className="hidden md:flex items-center gap-8">
              <a href="#how-it-works" className="text-sm text-gray-400 hover:text-white transition-colors">
                How it works
              </a>
              <a href="#features" className="text-sm text-gray-400 hover:text-white transition-colors">
                Features
              </a>
              <a href="#pricing" className="text-sm text-gray-400 hover:text-white transition-colors">
                Pricing
              </a>
              <a href="#faq" className="text-sm text-gray-400 hover:text-white transition-colors">
                FAQ
              </a>
            </div>
            <div className="flex items-center gap-3">
              <Link href="/dashboard">
                <Button variant="ghost" size="sm" className="text-gray-400 hover:text-white">
                  Dashboard
                </Button>
              </Link>
              <Button variant="gradient" size="sm">
                Get started free
              </Button>
            </div>
          </div>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section className="relative pt-32 pb-20 px-4 overflow-hidden">
        {/* Background gradient blobs */}
        <div
          aria-hidden
          className="absolute top-20 left-1/2 -translate-x-1/2 w-[800px] h-[500px] rounded-full bg-blue-600/10 blur-[120px] pointer-events-none"
        />
        <div
          aria-hidden
          className="absolute top-40 left-1/4 w-[400px] h-[400px] rounded-full bg-violet-600/10 blur-[100px] pointer-events-none"
        />

        <div className="relative max-w-7xl mx-auto">
          <div className="text-center mb-12">
            {/* Pill badge */}
            <div className="inline-flex items-center gap-2 rounded-full border border-blue-500/30 bg-blue-500/10 px-4 py-1.5 mb-8">
              <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse-slow" />
              <span className="text-xs font-medium text-blue-300">
                Now in public beta — free tier available
              </span>
            </div>

            <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold tracking-tight leading-tight mb-6">
              Incident at 3am?{" "}
              <span className="gradient-text">Diagnosed in 9 seconds.</span>
            </h1>

            <p className="max-w-2xl mx-auto text-lg sm:text-xl text-gray-400 leading-relaxed mb-10">
              SRE Copilot connects to your alerting pipeline, reads your runbooks, and
              posts root-cause + remediation steps to Slack before your phone wakes you up.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Button variant="gradient" size="lg" className="w-full sm:w-auto gap-2">
                Start for free
                <ArrowRight className="w-4 h-4" />
              </Button>
              <Button
                variant="outline"
                size="lg"
                className="w-full sm:w-auto gap-2 border-white/10 text-gray-300 hover:text-white hover:bg-white/5"
              >
                View live demo
              </Button>
            </div>
          </div>

          {/* Slack mockup */}
          <div className="max-w-2xl mx-auto">
            <SlackMockup />
          </div>

          <div className="text-center mt-8">
            <a href="#stats" className="inline-flex items-center gap-1 text-xs text-gray-500 hover:text-gray-400 transition-colors">
              <ChevronDown className="w-4 h-4" />
              See the numbers
            </a>
          </div>
        </div>
      </section>

      {/* ── Stats bar ── */}
      <section id="stats" className="py-12 border-y border-white/5 bg-white/[0.02]">
        <div className="max-w-5xl mx-auto px-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((stat) => (
              <div key={stat.label} className="text-center">
                <p className="text-3xl sm:text-4xl font-bold gradient-text mb-1">
                  {stat.value}
                </p>
                <p className="text-sm text-gray-500">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ── */}
      <section id="how-it-works" className="py-24 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">
              From alert to action in{" "}
              <span className="gradient-text">three steps</span>
            </h2>
            <p className="text-gray-400 max-w-xl mx-auto">
              No complex setup. No ML training. Just point your webhook, upload your runbooks, and SRE Copilot handles the rest.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 relative">
            {/* Connector line */}
            <div
              aria-hidden
              className="hidden md:block absolute top-10 left-[calc(33.3%-1px)] right-[calc(33.3%-1px)] h-px bg-gradient-to-r from-transparent via-white/10 to-transparent"
            />

            {steps.map((step, i) => (
              <div key={i} className="relative flex flex-col items-center text-center p-6">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-600/20 to-violet-600/20 border border-white/10 flex items-center justify-center mb-4 text-blue-400">
                  {step.icon}
                </div>
                <span className="text-xs font-bold text-gray-600 tracking-widest uppercase mb-2">
                  {step.number}
                </span>
                <h3 className="text-lg font-semibold text-white mb-2">{step.title}</h3>
                <p className="text-sm text-gray-400 leading-relaxed">{step.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section id="features" className="py-24 px-4 bg-white/[0.02] border-y border-white/5">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">
              Everything your on-call team needs
            </h2>
            <p className="text-gray-400 max-w-xl mx-auto">
              Built by SREs who have been paged at 3am one too many times.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, i) => (
              <Card
                key={i}
                className="bg-white/[0.03] border-white/10 hover:border-white/20 hover:bg-white/[0.05] transition-all duration-200 group"
              >
                <CardHeader className="pb-3">
                  <div className="w-10 h-10 rounded-lg bg-white/5 flex items-center justify-center mb-3 group-hover:scale-110 transition-transform duration-200">
                    {feature.icon}
                  </div>
                  <CardTitle className="text-base text-white">{feature.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-gray-400 text-sm leading-relaxed">
                    {feature.description}
                  </CardDescription>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pricing ── */}
      <section id="pricing" className="py-24 px-4">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">
              Simple, transparent pricing
            </h2>
            <p className="text-gray-400 max-w-xl mx-auto">
              Start free. Scale with your team. No per-seat nonsense.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {plans.map((plan, i) => (
              <div
                key={i}
                className={`relative rounded-2xl border p-8 flex flex-col ${
                  plan.highlighted
                    ? "border-blue-500/50 bg-gradient-to-b from-blue-950/40 to-violet-950/20 glow-blue"
                    : "border-white/10 bg-white/[0.02]"
                }`}
              >
                {plan.highlighted && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <span className="bg-gradient-to-r from-blue-600 to-violet-600 text-white text-xs font-bold px-4 py-1 rounded-full">
                      Most Popular
                    </span>
                  </div>
                )}

                <div className="mb-6">
                  <h3 className="text-lg font-bold text-white mb-1">{plan.name}</h3>
                  <p className="text-sm text-gray-400 mb-4">{plan.description}</p>
                  <div className="flex items-baseline gap-1">
                    <span className="text-4xl font-bold text-white">{plan.price}</span>
                    <span className="text-gray-500 text-sm">{plan.period}</span>
                  </div>
                </div>

                <ul className="space-y-3 flex-1 mb-8">
                  {plan.features.map((feature, j) => (
                    <li key={j} className="flex items-start gap-2 text-sm">
                      <CheckCircle2 className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5" />
                      <span className="text-gray-300">{feature}</span>
                    </li>
                  ))}
                </ul>

                <Button
                  className="w-full"
                  variant={plan.highlighted ? "gradient" : "outline"}
                >
                  {plan.cta}
                </Button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── FAQ ── */}
      <section id="faq" className="py-24 px-4 border-t border-white/5 bg-white/[0.02]">
        <div className="max-w-3xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">
              Frequently asked questions
            </h2>
          </div>

          <div className="space-y-4">
            {faqs.map((faq, i) => (
              <div
                key={i}
                className="rounded-xl border border-white/10 bg-white/[0.02] overflow-hidden"
              >
                <div className="flex items-start gap-4 p-6">
                  <div className="w-6 h-6 rounded-md bg-blue-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <ChevronDown className="w-3 h-3 text-blue-400" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white mb-2">{faq.q}</p>
                    <p className="text-sm text-gray-400 leading-relaxed">{faq.a}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA banner ── */}
      <section className="py-24 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="relative rounded-3xl border border-white/10 bg-gradient-to-b from-blue-950/40 to-violet-950/30 p-12 text-center overflow-hidden">
            <div
              aria-hidden
              className="absolute inset-0 bg-gradient-to-r from-blue-600/10 via-transparent to-violet-600/10 pointer-events-none"
            />
            <div className="relative">
              <Clock className="w-10 h-10 text-blue-400 mx-auto mb-4" />
              <h2 className="text-3xl sm:text-4xl font-bold mb-4">
                Stop waking up to alerts you can&apos;t diagnose.
              </h2>
              <p className="text-gray-400 max-w-xl mx-auto mb-8">
                Join the engineering teams shipping with confidence. Set up takes under 30 minutes.
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <Button variant="gradient" size="lg" className="gap-2">
                  Get started free
                  <ArrowRight className="w-4 h-4" />
                </Button>
                <Link href="/dashboard">
                  <Button
                    variant="outline"
                    size="lg"
                    className="border-white/10 text-gray-300 hover:text-white hover:bg-white/5"
                  >
                    Open dashboard
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-white/5 py-12 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
            <div className="col-span-2 md:col-span-1">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-600 to-violet-600 flex items-center justify-center">
                  <Zap className="w-3.5 h-3.5 text-white" />
                </div>
                <span className="font-bold text-white">SRE Copilot</span>
              </div>
              <p className="text-xs text-gray-500 leading-relaxed">
                AI-powered incident diagnosis for modern engineering teams.
              </p>
            </div>
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">
                Product
              </h4>
              <ul className="space-y-2 text-sm text-gray-400">
                <li><a href="#features" className="hover:text-white transition-colors">Features</a></li>
                <li><a href="#pricing" className="hover:text-white transition-colors">Pricing</a></li>
                <li><Link href="/dashboard" className="hover:text-white transition-colors">Dashboard</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">
                Resources
              </h4>
              <ul className="space-y-2 text-sm text-gray-400">
                <li><a href="#" className="hover:text-white transition-colors">Documentation</a></li>
                <li><a href="#" className="hover:text-white transition-colors">API Reference</a></li>
                <li><a href="#faq" className="hover:text-white transition-colors">FAQ</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">
                Company
              </h4>
              <ul className="space-y-2 text-sm text-gray-400">
                <li><a href="#" className="hover:text-white transition-colors">About</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Privacy</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Terms</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-white/5 pt-8 flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-xs text-gray-600">
              &copy; {new Date().getFullYear()} SRE Copilot. All rights reserved.
            </p>
            <p className="text-xs text-gray-600">
              Built for the engineers who keep the lights on.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
