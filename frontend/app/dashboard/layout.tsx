"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Zap,
  Bell,
  BookOpen,
  Settings,
  LayoutDashboard,
  Menu,
  X,
  ChevronRight,
  ExternalLink,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

const navItems = [
  {
    href: "/dashboard",
    label: "Alerts",
    icon: <Bell className="w-4 h-4" />,
    exact: true,
  },
  {
    href: "/dashboard/runbooks",
    label: "Runbooks",
    icon: <BookOpen className="w-4 h-4" />,
    exact: false,
  },
  {
    href: "/dashboard/settings",
    label: "Settings",
    icon: <Settings className="w-4 h-4" />,
    exact: false,
  },
];

function Sidebar({
  mobileOpen,
  onClose,
}: {
  mobileOpen: boolean;
  onClose: () => void;
}) {
  const pathname = usePathname();

  return (
    <>
      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar panel */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex flex-col w-60 border-r border-white/10 bg-[#0d0f14] transition-transform duration-300 lg:translate-x-0 lg:static lg:z-auto",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Logo */}
        <div className="flex items-center justify-between h-16 px-4 border-b border-white/10 flex-shrink-0">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-violet-600 flex items-center justify-center">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-white">SRE Copilot</span>
          </Link>
          <button
            onClick={onClose}
            className="lg:hidden text-gray-400 hover:text-white"
            aria-label="Close sidebar"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto">
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-600 px-3 mb-2">
            Main
          </p>
          {navItems.map((item) => {
            const isActive = item.exact
              ? pathname === item.href
              : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onClose}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150 group",
                  isActive
                    ? "bg-blue-600/20 text-blue-400 border border-blue-500/30"
                    : "text-gray-400 hover:text-white hover:bg-white/5"
                )}
              >
                <span
                  className={cn(
                    "transition-colors",
                    isActive ? "text-blue-400" : "text-gray-500 group-hover:text-white"
                  )}
                >
                  {item.icon}
                </span>
                {item.label}
                {isActive && (
                  <ChevronRight className="ml-auto w-3 h-3 text-blue-400/60" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* Footer links */}
        <div className="p-4 border-t border-white/10 flex-shrink-0">
          <Link
            href="/"
            className="flex items-center gap-2 text-xs text-gray-500 hover:text-gray-300 transition-colors"
          >
            <ExternalLink className="w-3 h-3" />
            Back to landing page
          </Link>
        </div>
      </aside>
    </>
  );
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const pathname = usePathname();

  // Page title from pathname
  const pageTitle = (() => {
    if (pathname === "/dashboard") return "Alert History";
    if (pathname.startsWith("/dashboard/runbooks")) return "Runbooks";
    if (pathname.startsWith("/dashboard/settings")) return "Settings";
    return "Dashboard";
  })();

  return (
    <div className="flex h-screen bg-[#0a0b0f] text-white overflow-hidden">
      <Sidebar
        mobileOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <header className="flex items-center justify-between h-16 px-4 sm:px-6 border-b border-white/10 bg-[#0d0f14] flex-shrink-0">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden text-gray-400 hover:text-white"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open sidebar"
            >
              <Menu className="w-5 h-5" />
            </Button>
            <div className="flex items-center gap-2 text-sm">
              <LayoutDashboard className="w-4 h-4 text-gray-500" />
              <span className="text-gray-500 hidden sm:inline">Dashboard</span>
              <ChevronRight className="w-3 h-3 text-gray-600 hidden sm:inline" />
              <span className="text-white font-medium">{pageTitle}</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Status indicator */}
            <div className="hidden sm:flex items-center gap-2 text-xs text-gray-500">
              <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse-slow" />
              <span>Connected</span>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
