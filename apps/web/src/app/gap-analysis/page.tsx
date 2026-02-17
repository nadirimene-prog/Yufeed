"use client";

import React, { useState, useEffect } from "react";
import {
  getGapDashboard,
  getGaps,
  getGapCategories,
  Gap,
  GapDashboard,
  CategoryCoverage,
} from "@/lib/gap-analysis-api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button-horizon";
import { Badge } from "@/components/ui/badge-horizon";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { AlertTriangle, CheckCircle, TrendingUp, Shield } from "lucide-react";
import { toast } from "@/components/ui/toast";

export default function GapAnalysisPage() {
  const [dashboard, setDashboard] = useState<GapDashboard | null>(null);
  const [gaps, setGaps] = useState<Gap[]>([]);
  const [categories, setCategories] = useState<CategoryCoverage[]>([]);
  const [loading, setLoading] = useState(true);
  const [severityFilter, setSeverityFilter] = useState<string>("");
  const [categoryFilter, setCategoryFilter] = useState<string>("");

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [dashboardData, gapsData, categoriesData] = await Promise.all([
        getGapDashboard(),
        getGaps({ limit: 10 }),
        getGapCategories(),
      ]);
      setDashboard(dashboardData);
      setGaps(gapsData.gaps);
      setCategories(categoriesData);
    } catch (_error) {
      toast({
        title: "Error",
        description: "Failed to load gap analysis data",
        variant: "error",
      });
      console.error(_error);
    } finally {
      setLoading(false);
    }
  };

  const handleFilter = async () => {
    try {
      setLoading(true);
      const data = await getGaps({
        severity: severityFilter as "critical" | "high" | "medium" | "low",
        category: categoryFilter || undefined,
        limit: 20,
      });
      setGaps(data.gaps);
    } catch (_error) {
      toast({
        title: "Error",
        description: "Failed to filter gaps",
        variant: "error",
      });
    } finally {
      setLoading(false);
    }
  };

  const _getSeverityColor = (severity: string) => {
    switch (severity) {
      case "critical":
        return "bg-red-500";
      case "high":
        return "bg-orange-500";
      case "medium":
        return "bg-yellow-500";
      default:
        return "bg-blue-500";
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case "critical":
        return <Badge variant="critical">Critical</Badge>;
      case "high":
        return <Badge variant="primary">High</Badge>;
      case "medium":
        return <Badge variant="secondary">Medium</Badge>;
      default:
        return <Badge variant="info">Low</Badge>;
    }
  };

  if (loading && !dashboard) {
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
            <Shield className="h-8 w-8" />
            Compliance Gap Analysis
          </h1>
          <p className="text-muted-foreground mt-1">
            Identify and track compliance gaps across your organization
          </p>
        </div>
        <Button onClick={loadData} variant="primary">
          Refresh
        </Button>
      </div>

      {/* Stats Cards */}
      {dashboard && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">
                Overall Coverage
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {dashboard.overall_coverage_percentage.toFixed(1)}%
              </div>
              <Progress
                value={dashboard.overall_coverage_percentage}
                className="mt-2"
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">
                Mapped Obligations
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {dashboard.mapped_obligations}
              </div>
              <p className="text-xs text-muted-foreground">
                of {dashboard.total_obligations} total
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-red-600">
                Critical Gaps
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">
                {dashboard.critical_gaps_count}
              </div>
              <p className="text-xs text-muted-foreground">
                {dashboard.high_gaps_count} high priority
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Unmapped</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-orange-500">
                {dashboard.unmapped_obligations}
              </div>
              <p className="text-xs text-muted-foreground">
                obligations need attention
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle>Filter Gaps</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <Select value={severityFilter} onValueChange={setSeverityFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Severity" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Severities</SelectItem>
                <SelectItem value="critical">Critical</SelectItem>
                <SelectItem value="high">High</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="low">Low</SelectItem>
              </SelectContent>
            </Select>

            <Select value={categoryFilter} onValueChange={setCategoryFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Categories</SelectItem>
                {categories.map((cat) => (
                  <SelectItem key={cat.category} value={cat.category}>
                    {cat.display_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Button onClick={handleFilter}>Apply Filters</Button>
          </div>
        </CardContent>
      </Card>

      {/* Gaps List */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" />
            Compliance Gaps
          </CardTitle>
        </CardHeader>
        <CardContent>
          {gaps.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <CheckCircle className="h-12 w-12 mx-auto mb-4 text-green-500" />
              <p>No gaps found matching your criteria.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {gaps.map((gap) => (
                <div
                  key={gap.obligation_id}
                  className="border rounded-lg p-4 hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        {getSeverityBadge(gap.severity)}
                        <Badge variant="primary">{gap.category}</Badge>
                        {gap.deadline_days !== null && (
                          <Badge
                            variant={
                              gap.deadline_days < 7 ? "critical" : "secondary"
                            }
                          >
                            {gap.deadline_days} days left
                          </Badge>
                        )}
                      </div>
                      <p className="text-sm">{gap.obligation_text}</p>
                      {gap.related_policies.length > 0 && (
                        <div className="mt-2 flex gap-2">
                          {gap.related_policies.map((policy) => (
                            <Badge
                              key={policy.policy_id}
                              variant="primary"
                              className="text-xs"
                            >
                              {policy.policy_name} ({policy.coverage_level})
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Category Coverage */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Coverage by Category
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {categories.map((cat) => (
              <div key={cat.category} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">{cat.display_name}</span>
                  <Badge
                    variant={
                      cat.coverage_percentage >= 80 ? "default" : "secondary"
                    }
                  >
                    {cat.coverage_percentage.toFixed(1)}%
                  </Badge>
                </div>
                <Progress value={cat.coverage_percentage} className="h-2" />
                <p className="text-xs text-muted-foreground mt-2">
                  {cat.mapped_obligations} of {cat.total_obligations}{" "}
                  obligations mapped
                </p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
