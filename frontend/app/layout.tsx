import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "SRE Copilot — AI-Powered Incident Diagnosis",
  description:
    "Stop firefighting blind. SRE Copilot diagnoses production incidents in under 10 seconds using AI, your runbooks, and live telemetry.",
  keywords: ["SRE", "incident management", "AI", "on-call", "MTTR", "DevOps"],
  authors: [{ name: "SRE Copilot" }],
  openGraph: {
    title: "SRE Copilot — AI-Powered Incident Diagnosis",
    description:
      "Diagnose production incidents in under 10 seconds. Reduce MTTR by 89%.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} antialiased`}>{children}</body>
    </html>
  );
}
