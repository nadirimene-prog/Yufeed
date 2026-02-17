"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  getUpcomingDeadlines,
  getReminderStatistics,
  getReminderSubscriptions,
  createReminderSubscription,
  deleteReminderSubscription,
  snoozeReminders,
  UpcomingDeadline,
  ReminderStatistics,
  ReminderSubscription,
} from "@/lib/reminders-api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button-horizon";
import { Badge } from "@/components/ui/badge-horizon";

import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Bell,
  AlarmClock,
  Calendar,
  AlertTriangle,
  CheckCircle,
  Clock,
  Plus,
  Trash2,
} from "lucide-react";
import { toast } from "@/components/ui/toast";

export default function RemindersPage() {
  const [deadlines, setDeadlines] = useState<UpcomingDeadline[]>([]);
  const [stats, setStats] = useState<ReminderStatistics | null>(null);
  const [subscriptions, setSubscriptions] = useState<ReminderSubscription[]>(
    [],
  );
  const [loading, setLoading] = useState(true);
  const [daysFilter, setDaysFilter] = useState<number>(30);
  const [showAddSubscription, setShowAddSubscription] = useState(false);
  const [newSubscription, setNewSubscription] = useState({
    obligation_id: "",
    category: "",
    reminder_days: [7, 3, 1],
    channels: ["email"],
  });

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [deadlinesData, statsData, subscriptionsData] = await Promise.all([
        getUpcomingDeadlines({ days: daysFilter }),
        getReminderStatistics(),
        getReminderSubscriptions(),
      ]);
      setDeadlines(deadlinesData);
      setStats(statsData);
      setSubscriptions(subscriptionsData);
    } catch (_error) {
      toast({
        title: "Error",
        description: "Failed to load reminders data",
        variant: "error",
      });
    } finally {
      setLoading(false);
    }
  }, [daysFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSnooze = async (obligationId: string) => {
    try {
      await snoozeReminders(obligationId, 24, "User requested snooze");
      toast({
        title: "Success",
        description: "Reminders snoozed for 24 hours",
        variant: "success",
      });
      loadData();
    } catch (_error) {
      toast({
        title: "Error",
        description: "Failed to snooze reminders",
        variant: "error",
      });
    }
  };

  const handleCreateSubscription = async () => {
    try {
      await createReminderSubscription({
        obligation_id: newSubscription.obligation_id || undefined,
        category: newSubscription.category || undefined,
        reminder_days: newSubscription.reminder_days,
        channels: newSubscription.channels,
      });
      toast({
        title: "Success",
        description: "Subscription created",
        variant: "success",
      });
      setShowAddSubscription(false);
      loadData();
    } catch (_error) {
      toast({
        title: "Error",
        description: "Failed to create subscription",
        variant: "error",
      });
    }
  };

  const handleDeleteSubscription = async (id: string) => {
    try {
      await deleteReminderSubscription(id);
      toast({
        title: "Success",
        description: "Subscription deleted",
        variant: "success",
      });
      loadData();
    } catch (_error) {
      toast({
        title: "Error",
        description: "Failed to delete subscription",
        variant: "error",
      });
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "critical":
        return "text-red-600 bg-red-50";
      case "high":
        return "text-orange-600 bg-orange-50";
      case "medium":
        return "text-yellow-600 bg-yellow-50";
      default:
        return "text-blue-600 bg-blue-50";
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case "critical":
        return <AlertTriangle className="h-5 w-5 text-red-600" />;
      case "high":
        return <AlertTriangle className="h-5 w-5 text-orange-600" />;
      default:
        return <Clock className="h-5 w-5 text-blue-600" />;
    }
  };

  if (loading && !stats) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Bell className="h-8 w-8" />
            Deadline Reminders
          </h1>
          <p className="text-muted-foreground mt-1">
            Track upcoming compliance deadlines and manage notifications
          </p>
        </div>
        <div className="flex gap-2">
          <Select
            value={daysFilter.toString()}
            onValueChange={(v) => setDaysFilter(parseInt(v))}
          >
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="Timeframe" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">Next 7 days</SelectItem>
              <SelectItem value="14">Next 14 days</SelectItem>
              <SelectItem value="30">Next 30 days</SelectItem>
              <SelectItem value="90">Next 90 days</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="primary" onClick={loadData}>
            Refresh
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">
                Total Upcoming
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_upcoming}</div>
              <p className="text-xs text-muted-foreground">
                deadlines in period
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-red-600">
                Critical
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">
                {stats.critical}
              </div>
              <p className="text-xs text-muted-foreground">
                require immediate action
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-orange-600">
                High
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-orange-600">
                {stats.high}
              </div>
              <p className="text-xs text-muted-foreground">
                priority deadlines
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">
                Subscriptions
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{subscriptions.length}</div>
              <p className="text-xs text-muted-foreground">
                active reminder settings
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Deadlines List */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-5 w-5" />
                Upcoming Deadlines
              </CardTitle>
            </CardHeader>
            <CardContent>
              {deadlines.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <CheckCircle className="h-12 w-12 mx-auto mb-4 text-green-500" />
                  <p>No upcoming deadlines in the selected period.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {deadlines.map((deadline, idx) => (
                    <div
                      key={idx}
                      className={`border rounded-lg p-4 ${getSeverityColor(
                        deadline.severity,
                      )}`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            {getSeverityIcon(deadline.severity)}
                            <Badge
                              variant={
                                deadline.days_remaining < 3
                                  ? "critical"
                                  : "default"
                              }
                            >
                              {deadline.days_remaining} days left
                            </Badge>
                            <Badge variant="primary">{deadline.category}</Badge>
                          </div>
                          <p className="font-medium">
                            {deadline.obligation_text}
                          </p>
                          <p className="text-sm mt-1">
                            Deadline:{" "}
                            {new Date(deadline.deadline).toLocaleDateString()}
                          </p>
                          {deadline.related_documents.length > 0 && (
                            <div className="mt-2 flex gap-2">
                              {deadline.related_documents.map((doc, idx) => (
                                <Badge
                                  key={idx}
                                  variant="primary"
                                  className="text-xs"
                                >
                                  {doc.celex}
                                </Badge>
                              ))}
                            </div>
                          )}
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleSnooze(deadline.obligation_id)}
                        >
                          <AlarmClock className="h-4 w-4 mr-1" />
                          Snooze
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Subscriptions Panel */}
        <div className="space-y-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Bell className="h-5 w-5" />
                Subscriptions
              </CardTitle>
              <Dialog
                open={showAddSubscription}
                onOpenChange={setShowAddSubscription}
              >
                <DialogTrigger asChild>
                  <Button size="sm">
                    <Plus className="h-4 w-4 mr-1" />
                    Add
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>New Reminder Subscription</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4 pt-4">
                    <div>
                      <Label>Obligation ID (optional)</Label>
                      <Input
                        placeholder="e.g., obl-001"
                        value={newSubscription.obligation_id}
                        onChange={(e) =>
                          setNewSubscription({
                            ...newSubscription,
                            obligation_id: e.target.value,
                          })
                        }
                      />
                    </div>
                    <div>
                      <Label>Category (optional)</Label>
                      <Input
                        placeholder="e.g., AML"
                        value={newSubscription.category}
                        onChange={(e) =>
                          setNewSubscription({
                            ...newSubscription,
                            category: e.target.value,
                          })
                        }
                      />
                    </div>
                    <Button
                      onClick={handleCreateSubscription}
                      className="w-full"
                    >
                      Create Subscription
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent>
              {subscriptions.length === 0 ? (
                <p className="text-center text-muted-foreground py-4">
                  No active subscriptions
                </p>
              ) : (
                <div className="space-y-3">
                  {subscriptions.map((sub) => (
                    <div
                      key={sub.id}
                      className="border rounded-lg p-3 flex items-center justify-between"
                    >
                      <div>
                        <div className="font-medium text-sm">
                          {sub.obligation_id ??
                            sub.category ??
                            "All obligations"}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {sub.reminder_days.join(", ")} days before
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteSubscription(sub.id)}
                      >
                        <Trash2 className="h-4 w-4 text-red-500" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
