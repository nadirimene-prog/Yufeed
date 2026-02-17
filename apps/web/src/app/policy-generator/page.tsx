"use client";

import React, { useState, useEffect } from "react";
import {
  getPolicyTemplates,
  getTemplateVariables,
  generatePolicy,
  getGenerationJobs,
  getGenerationResult,
  approveGeneratedPolicy,
  rejectGeneratedPolicy,
  PolicyTemplate,
  TemplateVariable,
  GenerationJob,
  PolicyGenerationResult,
} from "@/lib/policy-generator-api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button-horizon";
import { Badge } from "@/components/ui/badge-horizon";
import { Input, Textarea } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { FileText, Wand2, Clock, CheckCircle, XCircle } from "lucide-react";
import { toast } from "@/components/ui/toast";

export default function PolicyGeneratorPage() {
  const [templates, setTemplates] = useState<PolicyTemplate[]>([]);
  const [jobs, setJobs] = useState<GenerationJob[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string>("");
  const [templateVars, setTemplateVars] = useState<TemplateVariable[]>([]);
  const [variableValues, setVariableValues] = useState<Record<string, string>>(
    {},
  );
  const [obligationIds, setObligationIds] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"generate" | "jobs">("generate");
  const [selectedJob, setSelectedJob] = useState<PolicyGenerationResult | null>(
    null,
  );

  useEffect(() => {
    loadTemplates();
    loadJobs();
  }, []);

  useEffect(() => {
    if (selectedTemplate) {
      loadTemplateVariables(selectedTemplate);
    }
  }, [selectedTemplate]);

  const loadTemplates = async () => {
    try {
      const data = await getPolicyTemplates();
      setTemplates(data.templates);
    } catch (_error) {
      toast({
        title: "Error",
        description: "Failed to load templates",
        variant: "error",
      });
    }
  };

  const loadJobs = async () => {
    try {
      const data = await getGenerationJobs();
      setJobs(data.jobs);
    } catch (_error) {
      toast({
        title: "Error",
        description: "Failed to load generation jobs",
        variant: "error",
      });
    }
  };

  const loadTemplateVariables = async (templateId: string) => {
    try {
      const vars = await getTemplateVariables(templateId);
      setTemplateVars(vars);
      // Initialize with defaults
      const defaults: Record<string, string> = {};
      vars.forEach((v) => {
        if (v.default_value) defaults[v.name] = v.default_value;
      });
      setVariableValues(defaults);
    } catch (_error) {
      toast({
        title: "Error",
        description: "Failed to load template variables",
        variant: "error",
      });
    }
  };

  const handleGenerate = async () => {
    if (!selectedTemplate) {
      toast({
        title: "Error",
        description: "Please select a template",
        variant: "error",
      });
      return;
    }

    try {
      setLoading(true);
      const obligationIdsList = obligationIds
        .split(",")
        .map((id) => id.trim())
        .filter((id) => id);

      const result = await generatePolicy({
        template_id: selectedTemplate,
        obligation_ids: obligationIdsList,
        custom_variables: variableValues,
        options: {
          include_procedures: true,
          include_controls: true,
          tone: "formal",
        },
      });

      toast({
        title: "Success",
        description: `Policy generation started! Job ID: ${result.job_id}`,
        variant: "success",
      });
      setActiveTab("jobs");
      loadJobs();
    } catch (_error) {
      toast({
        title: "Error",
        description: "Failed to start policy generation",
        variant: "error",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleViewResult = async (jobId: string) => {
    try {
      const result = await getGenerationResult(jobId);
      setSelectedJob(result);
    } catch (_error) {
      toast({
        title: "Error",
        description: "Failed to load generation result",
        variant: "error",
      });
    }
  };

  const handleApprove = async (jobId: string) => {
    try {
      await approveGeneratedPolicy(jobId);
      toast({
        title: "Success",
        description: "Policy approved and created!",
        variant: "success",
      });
      loadJobs();
      setSelectedJob(null);
    } catch (_error) {
      toast({
        title: "Error",
        description: "Failed to approve policy",
        variant: "error",
      });
    }
  };

  const handleReject = async (jobId: string) => {
    try {
      await rejectGeneratedPolicy(jobId, "Not suitable");
      toast({
        title: "Success",
        description: "Policy rejected",
        variant: "success",
      });
      loadJobs();
      setSelectedJob(null);
    } catch (_error) {
      toast({
        title: "Error",
        description: "Failed to reject policy",
        variant: "error",
      });
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "completed":
        return <Badge variant="primary">Completed</Badge>;
      case "processing":
        return <Badge variant="secondary">Processing</Badge>;
      case "queued":
        return <Badge variant="primary">Queued</Badge>;
      case "failed":
        return <Badge variant="critical">Failed</Badge>;
      default:
        return <Badge>{status}</Badge>;
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Wand2 className="h-8 w-8" />
            AI Policy Generator
          </h1>
          <p className="text-muted-foreground mt-1">
            Generate compliance policies from obligations using AI
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant={activeTab === "generate" ? "primary" : "secondary"}
            onClick={() => setActiveTab("generate")}
          >
            Generate New
          </Button>
          <Button
            variant={activeTab === "jobs" ? "primary" : "secondary"}
            onClick={() => setActiveTab("jobs")}
          >
            <Clock className="h-4 w-4 mr-2" />
            Jobs ({jobs.length})
          </Button>
        </div>
      </div>

      {activeTab === "generate" ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Template Selection */}
          <Card>
            <CardHeader>
              <CardTitle>1. Select Template</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Select
                value={selectedTemplate}
                onValueChange={setSelectedTemplate}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Choose a policy template" />
                </SelectTrigger>
                <SelectContent>
                  {templates.map((template) => (
                    <SelectItem
                      key={template.template_id}
                      value={template.template_id}
                    >
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4" />
                        <span>{template.name}</span>
                        <Badge variant="primary" className="ml-2">
                          {template.category}
                        </Badge>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {selectedTemplate && (
                <div className="p-4 bg-muted rounded-lg">
                  <p className="text-sm text-muted-foreground">
                    {
                      templates.find((t) => t.template_id === selectedTemplate)
                        ?.description
                    }
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Obligations */}
          <Card>
            <CardHeader>
              <CardTitle>2. Link Obligations</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Label htmlFor="obligations">
                Obligation IDs (comma-separated)
              </Label>
              <Textarea
                id="obligations"
                placeholder="e.g., obl-001, obl-002, obl-003"
                value={obligationIds}
                onChange={(e) => setObligationIds(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Enter the obligation IDs this policy should address
              </p>
            </CardContent>
          </Card>

          {/* Template Variables */}
          {templateVars.length > 0 && (
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>3. Customize Variables</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {templateVars.map((variable) => (
                    <div key={variable.name} className="space-y-2">
                      <Label htmlFor={variable.name}>
                        {variable.name}
                        {variable.required && (
                          <span className="text-red-500 ml-1">*</span>
                        )}
                      </Label>
                      <Input
                        id={variable.name}
                        value={variableValues[variable.name] || ""}
                        onChange={(e) =>
                          setVariableValues({
                            ...variableValues,
                            [variable.name]: e.target.value,
                          })
                        }
                        placeholder={variable.default_value}
                      />
                      <p className="text-xs text-muted-foreground">
                        {variable.description}
                      </p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Generate Button */}
          <div className="lg:col-span-2">
            <Button
              size="lg"
              className="w-full"
              onClick={handleGenerate}
              disabled={loading || !selectedTemplate}
            >
              {loading ? (
                <>
                  <div className="animate-spin mr-2 h-4 w-4 border-2 border-current border-t-transparent rounded-full" />
                  Generating...
                </>
              ) : (
                <>
                  <Wand2 className="h-5 w-5 mr-2" />
                  Generate Policy
                </>
              )}
            </Button>
          </div>
        </div>
      ) : (
        /* Jobs List */
        <Card>
          <CardHeader>
            <CardTitle>Generation Jobs</CardTitle>
          </CardHeader>
          <CardContent>
            {jobs.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Clock className="h-12 w-12 mx-auto mb-4" />
                <p>No generation jobs yet.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {jobs.map((job) => (
                  <div
                    key={job.job_id}
                    className="border rounded-lg p-4 flex items-center justify-between"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{job.job_id}</span>
                        {getStatusBadge(job.status)}
                      </div>
                      <p className="text-sm text-muted-foreground">
                        Template: {job.template_id} • Created:{" "}
                        {new Date(job.created_at).toLocaleString()}
                      </p>
                    </div>
                    {job.status === "completed" && (
                      <Dialog>
                        <DialogTrigger asChild>
                          <Button
                            variant="primary"
                            onClick={() => handleViewResult(job.job_id)}
                          >
                            View Result
                          </Button>
                        </DialogTrigger>
                        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
                          <DialogHeader>
                            <DialogTitle>Generated Policy</DialogTitle>
                          </DialogHeader>
                          {selectedJob && (
                            <div className="space-y-4">
                              <div className="flex items-center gap-2">
                                <Badge>
                                  AI Confidence: {selectedJob.ai_confidence}%
                                </Badge>
                                <Badge variant="primary">
                                  {selectedJob.word_count} words
                                </Badge>
                              </div>
                              <div className="space-y-4">
                                {selectedJob.sections.map((section, idx) => (
                                  <div
                                    key={idx}
                                    className="border rounded-lg p-4"
                                  >
                                    <h3 className="font-semibold mb-2">
                                      {section.title}
                                    </h3>
                                    <div className="text-sm whitespace-pre-wrap">
                                      {section.content}
                                    </div>
                                  </div>
                                ))}
                              </div>
                              <div className="flex gap-2 pt-4">
                                <Button
                                  onClick={() => handleApprove(job.job_id)}
                                  className="flex-1"
                                >
                                  <CheckCircle className="h-4 w-4 mr-2" />
                                  Approve & Create Policy
                                </Button>
                                <Button
                                  variant="destructive"
                                  onClick={() => handleReject(job.job_id)}
                                >
                                  <XCircle className="h-4 w-4 mr-2" />
                                  Reject
                                </Button>
                              </div>
                            </div>
                          )}
                        </DialogContent>
                      </Dialog>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
