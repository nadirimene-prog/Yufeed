"use client";

import * as React from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button-horizon";
import { Badge, RiskBadge, StatusBadge } from "@/components/ui/badge-horizon";
import { PageHeader, PageGrid, PageSection } from "@/components/app-shell-new";
import {
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  FileText,
  Gavel,
  Shield,
  Clock,
  ArrowUpRight,
  Activity,
  CheckCircle2,
  XCircle,
  AlertCircle,
  MoreHorizontal,
} from "lucide-react";

/**
 * Horizon Dashboard
 * Modern, data-rich command center for compliance monitoring
 */

// Pre-define motion components outside render to avoid creating components during render
const MotionLink = motion(Link);
const MotionDiv = motion.div;

/* ─────────────────────────────────────────────────────────────────────────────
   Metric Card Component
   ───────────────────────────────────────────────────────────────────────────── */

interface MetricCardProps {
  title: string;
  value: string | number;
  change?: {
    value: number;
    trend: "up" | "down" | "neutral";
  };
  icon: React.ReactNode;
  variant?: "default" | "critical" | "warning" | "success";
  href?: string;
}

function MetricCard({
  title,
  value,
  change,
  icon,
  variant = "default",
  href,
}: MetricCardProps) {
  const variantStyles = {
    default: "bg-bg-elevated border-border-subtle",
    critical: "bg-critical-500/10 border-critical-500/20",
    warning: "bg-warning-500/10 border-warning-500/20",
    success: "bg-success-500/10 border-success-500/20",
  }[variant];

  const iconStyles = {
    default: "bg-primary/10 text-primary",
    critical: "bg-critical-500/20 text-critical-400",
    warning: "bg-warning-500/20 text-warning-400",
    success: "bg-success-500/20 text-success-400",
  }[variant];

  const content = (
    <div className="flex items-start justify-between">
      <div>
        <p className="text-sm font-medium text-text-secondary">{title}</p>
        <p className="mt-1 text-2xl font-semibold text-text-primary">{value}</p>
        {change && (
          <div className="mt-2 flex items-center gap-1">
            {change.trend === "up" ? (
              <TrendingUp className="h-3 w-3 text-success-500" />
            ) : change.trend === "down" ? (
              <TrendingDown className="h-3 w-3 text-critical-500" />
            ) : null}
            <span
              className={cn(
                "text-xs font-medium",
                change.trend === "up"
                  ? "text-success-500"
                  : change.trend === "down"
                    ? "text-critical-500"
                    : "text-text-secondary",
              )}
            >
              {change.value > 0 ? "+" : ""}
              {change.value}%
            </span>
          </div>
        )}
      </div>
      <div className={cn("rounded-lg p-2.5", iconStyles)}>{icon}</div>
    </div>
  );

  if (href) {
    return (
      <MotionLink
        href={href}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        whileHover={{ y: -2 }}
        transition={{ duration: 0.2 }}
        className={cn(
          "block rounded-xl border p-5 transition-all hover:shadow-md cursor-pointer",
          variantStyles,
        )}
      >
        {content}
      </MotionLink>
    );
  }

  return (
    <MotionDiv
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={cn("rounded-xl border p-5", variantStyles)}
    >
      {content}
    </MotionDiv>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Activity Feed Component
   ───────────────────────────────────────────────────────────────────────────── */

interface ActivityItem {
  id: string;
  type: "alert" | "case" | "document" | "decision" | "system";
  title: string;
  description: string;
  timestamp: string;
  status?: "success" | "warning" | "error" | "info";
}

const recentActivity: ActivityItem[] = [
  {
    id: "1",
    type: "alert",
    title: "High-Risk Transaction Detected",
    description: "Case #45231 flagged for review",
    timestamp: "5 min ago",
    status: "warning",
  },
  {
    id: "2",
    type: "document",
    title: "New Regulation Published",
    description: "AML Directive 2024/1234 now in effect",
    timestamp: "1 hour ago",
    status: "info",
  },
  {
    id: "3",
    type: "decision",
    title: "SAR Filed",
    description: "Suspicious Activity Report submitted",
    timestamp: "2 hours ago",
    status: "success",
  },
  {
    id: "4",
    type: "case",
    title: "Case Escalated",
    description: "Case #45225 moved to senior review",
    timestamp: "3 hours ago",
    status: "error",
  },
];

function ActivityFeed() {
  const getIcon = (
    type: ActivityItem["type"],
    status?: ActivityItem["status"],
  ) => {
    const iconClass = "h-4 w-4";
    switch (status) {
      case "success":
        return <CheckCircle2 className={cn(iconClass, "text-success-500")} />;
      case "warning":
        return <AlertCircle className={cn(iconClass, "text-warning-500")} />;
      case "error":
        return <XCircle className={cn(iconClass, "text-critical-500")} />;
      default:
        return (
          <Activity className={cn(iconClass, "text-foreground-tertiary")} />
        );
    }
  };

  return (
    <Card variant="default" padding="none">
      <CardHeader padding="md">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>
              Latest events across your workspace
            </CardDescription>
          </div>
          <Button variant="ghost" size="sm">
            View all
          </Button>
        </div>
      </CardHeader>
      <CardContent padding="none">
        <ul className="divide-y divide-border-subtle">
          {recentActivity.map((item, index) => (
            <motion.li
              key={item.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.05 }}
              className="flex items-start gap-3 p-4 hover:bg-bg-overlay transition-colors"
            >
              <div className="mt-0.5">{getIcon(item.type, item.status)}</div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground">
                  {item.title}
                </p>
                <p className="text-sm text-foreground-secondary truncate">
                  {item.description}
                </p>
              </div>
              <span className="text-xs text-foreground-tertiary whitespace-nowrap">
                {item.timestamp}
              </span>
            </motion.li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Quick Actions Component
   ───────────────────────────────────────────────────────────────────────────── */

const quickActions = [
  {
    label: "Create Case",
    description: "Start a new investigation",
    icon: Gavel,
    href: "/cases/new",
    color: "text-primary",
    bgColor: "bg-primary/10",
  },
  {
    label: "Submit SAR",
    description: "File suspicious activity report",
    icon: FileText,
    href: "/sar/prepare",
    color: "text-warning-400",
    bgColor: "bg-warning-500/10",
  },
  {
    label: "Review Alerts",
    description: "Check pending notifications",
    icon: AlertTriangle,
    href: "/alerts",
    color: "text-critical-400",
    bgColor: "bg-critical-500/10",
    badge: 5,
  },
  {
    label: "Compliance Check",
    description: "Run automated audit",
    icon: Shield,
    href: "/compliance",
    color: "text-success-400",
    bgColor: "bg-success-500/10",
  },
];

function QuickActions() {
  return (
    <PageSection title="Quick Actions">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {quickActions.map((action, index) => (
          <motion.div
            key={action.label}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
          >
            <Link
              href={action.href}
              className="group flex items-center gap-3 rounded-xl border border-border-subtle bg-bg-elevated p-4 transition-all hover:border-border-default hover:shadow-sm hover:-translate-y-0.5"
            >
              <div
                className={cn(
                  "rounded-lg p-2.5 transition-colors",
                  action.bgColor,
                )}
              >
                <action.icon className={cn("h-5 w-5", action.color)} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-foreground">
                    {action.label}
                  </span>
                  {"badge" in action && action.badge && (
                    <Badge variant="critical" size="sm">
                      {action.badge}
                    </Badge>
                  )}
                </div>
                <p className="text-sm text-foreground-secondary">
                  {action.description}
                </p>
              </div>
              <ArrowUpRight className="h-4 w-4 text-foreground-tertiary group-hover:text-foreground transition-colors" />
            </Link>
          </motion.div>
        ))}
      </div>
    </PageSection>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Pending Tasks Component
   ───────────────────────────────────────────────────────────────────────────── */

interface Task {
  id: string;
  title: string;
  dueDate: string;
  priority: "high" | "medium" | "low";
  assignee: string;
}

const pendingTasks: Task[] = [
  {
    id: "1",
    title: "Review AML Policy Updates",
    dueDate: "Today",
    priority: "high",
    assignee: "You",
  },
  {
    id: "2",
    title: "Approve SAR Filing",
    dueDate: "Tomorrow",
    priority: "high",
    assignee: "You",
  },
  {
    id: "3",
    title: "Quarterly Compliance Report",
    dueDate: "3 days",
    priority: "medium",
    assignee: "Team",
  },
];

function PendingTasks() {
  return (
    <Card variant="default" padding="none">
      <CardHeader padding="md">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Pending Tasks</CardTitle>
            <CardDescription>Action items requiring attention</CardDescription>
          </div>
          <Button variant="ghost" size="icon-sm" aria-label="More options">
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent padding="md">
        <ul className="space-y-3">
          {pendingTasks.map((task) => (
            <li
              key={task.id}
              className="flex items-start gap-3 rounded-lg border border-border-subtle bg-bg-overlay p-3 hover:border-border-default transition-colors"
            >
              <div className="mt-0.5">
                <Clock className="h-4 w-4 text-foreground-tertiary" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-foreground text-sm">
                    {task.title}
                  </span>
                  <RiskBadge
                    level={
                      task.priority === "high"
                        ? "critical"
                        : task.priority === "medium"
                          ? "medium"
                          : "low"
                    }
                    size="sm"
                    showDot={false}
                  >
                    {task.priority}
                  </RiskBadge>
                </div>
                <div className="mt-1 flex items-center gap-2 text-xs text-foreground-secondary">
                  <span>Due {task.dueDate}</span>
                  <span>•</span>
                  <span>{task.assignee}</span>
                </div>
              </div>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Main Dashboard Page
   ───────────────────────────────────────────────────────────────────────────── */

import { cn } from "@/lib/utils";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <PageHeader
        title="Dashboard"
        description="Welcome back, John. Here's what's happening in your compliance workspace."
      >
        <Button variant="primary" leftIcon={<FileText className="h-4 w-4" />}>
          New Report
        </Button>
      </PageHeader>

      {/* Metrics */}
      <PageGrid columns={4} gap="md">
        <MetricCard
          title="Active Cases"
          value={24}
          change={{ value: 12, trend: "up" }}
          icon={<Gavel className="h-5 w-5" />}
          href="/cases"
        />
        <MetricCard
          title="Pending Alerts"
          value={8}
          change={{ value: -5, trend: "down" }}
          icon={<AlertTriangle className="h-5 w-5" />}
          variant="warning"
          href="/alerts"
        />
        <MetricCard
          title="Compliance Score"
          value="94%"
          change={{ value: 2, trend: "up" }}
          icon={<Shield className="h-5 w-5" />}
          variant="success"
        />
        <MetricCard
          title="Critical Issues"
          value={2}
          icon={<AlertTriangle className="h-5 w-5" />}
          variant="critical"
          href="/compliance/obligations"
        />
      </PageGrid>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Activity & Quick Actions */}
        <div className="lg:col-span-2 space-y-6">
          <QuickActions />
          <ActivityFeed />
        </div>

        {/* Right Column - Tasks & Insights */}
        <div className="space-y-6">
          <PendingTasks />

          {/* System Status */}
          <Card variant="default">
            <CardHeader>
              <CardTitle>System Status</CardTitle>
              <CardDescription>Service health overview</CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-3">
                {[
                  { service: "API", status: "operational" },
                  { service: "Data Pipeline", status: "operational" },
                  { service: "AI Services", status: "degraded" },
                  { service: "Notifications", status: "operational" },
                ].map((item) => (
                  <li
                    key={item.service}
                    className="flex items-center justify-between"
                  >
                    <span className="text-sm text-foreground-secondary">
                      {item.service}
                    </span>
                    <StatusBadge
                      status={
                        item.status === "operational"
                          ? "approved"
                          : item.status === "degraded"
                            ? "warning"
                            : "critical"
                      }
                      size="sm"
                    >
                      {item.status}
                    </StatusBadge>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          {/* AI Insight Card */}
          <Card
            variant="default"
            className="bg-gradient-to-br from-primary/5 to-secondary/5"
          >
            <CardContent className="p-5">
              <div className="flex items-start gap-3">
                <div className="rounded-lg bg-primary/10 p-2">
                  <Shield className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <h4 className="font-medium text-foreground">AI Insight</h4>
                  <p className="mt-1 text-sm text-foreground-secondary">
                    Based on recent activity, consider reviewing 3 cases that
                    show patterns similar to previously escalated alerts.
                  </p>
                  <Button variant="link" size="sm" className="mt-2 px-0">
                    Review cases →
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
