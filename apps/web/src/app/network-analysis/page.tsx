"use client";

import { useState } from "react";
import { Network, Search, AlertTriangle, Users, Activity } from "lucide-react";
import toast from "react-hot-toast";
import dynamic from "next/dynamic";
import { fetchWithAuth } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/apiBaseUrl";
import { logger } from "@/lib/logger";

// Dynamically import NetworkGraph to avoid SSR issues
const NetworkGraph = dynamic(() => import("@/components/NetworkGraph"), {
  ssr: false,
});

const API_URL = getApiBaseUrl();

interface CircularFlow {
  path: string[];
  transaction_count: number;
  total_amount: number;
}

interface SuspiciousCluster {
  member_count: number;
  cluster_risk_score: number;
}

interface NetworkAnalysis {
  user_id: string;
  network_size: number;
  connection_count: number;
  depth_analyzed: number;
  period_days: number;
  network: {
    nodes: string[];
    node_details: Record<
      string,
      {
        user_id: string;
        risk_level: string;
        risk_score: number;
        total_alerts: number;
      }
    >;
    edges: {
      source: string;
      target: string;
      type: string;
      amount: number;
      currency: string;
      timestamp: string;
      transaction_id: string;
    }[];
  };
  risk_indicators: {
    circular_flows: CircularFlow[];
    shared_attributes: {
      shared_ips?: Record<string, string[]>;
      shared_devices?: Record<string, string[]>;
    };
    suspicious_clusters: SuspiciousCluster[];
  };
  network_risk_score: number;
  risk_level: string;
}

interface FraudRing {
  ring_id: string;
  size: number;
  members: string[];
  transaction_count: number;
  total_volume: number;
  risk_score: number;
  indicators: string[];
}

export default function NetworkAnalysisPage() {
  const [userId, setUserId] = useState("");
  const [depth, setDepth] = useState(2);
  const [days, setDays] = useState(90);
  const [networkData, setNetworkData] = useState<NetworkAnalysis | null>(null);
  const [fraudRings, setFraudRings] = useState<FraudRing[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"user" | "rings">("user");

  const analyzeUserNetwork = async () => {
    if (!userId) {
      toast.error("Please enter a user ID");
      return;
    }

    const toastId = toast.loading("Analyzing network...");
    setLoading(true);
    try {
      const res = await fetchWithAuth(
        `${API_URL}/api/network/analyze/${userId}?depth=${depth}&days=${days}`,
      );
      const data = await res.json();
      setNetworkData(data);
      toast.success(`Network analyzed: ${data.network_size} nodes found`, {
        id: toastId,
      });
    } catch (error) {
      logger.error("Error analyzing network:", error);
      toast.error("Failed to analyze network", { id: toastId });
    } finally {
      setLoading(false);
    }
  };

  const detectFraudRings = async () => {
    const toastId = toast.loading("Scanning for fraud rings...");
    setLoading(true);
    try {
      const res = await fetchWithAuth(
        `${API_URL}/api/network/fraud-rings/detect`,
      );
      const data = await res.json();
      setFraudRings(data.rings ?? []);
      toast.success(`Found ${data.rings?.length ?? 0} potential fraud rings`, {
        id: toastId,
      });
    } catch (error) {
      logger.error("Error detecting fraud rings:", error);
      toast.error("Failed to detect fraud rings", { id: toastId });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50  p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900  mb-2">
            Network Analysis & Fraud Detection
          </h1>
          <p className="text-slate-600 ">
            Analyze transaction networks and detect fraud rings
          </p>
        </div>

        {/* Tabs */}
        <div className="flex gap-4 mb-6">
          <button
            onClick={() => setActiveTab("user")}
            className={`px-6 py-3 rounded-lg font-medium transition ${
              activeTab === "user"
                ? "bg-blue-600 text-white"
                : "bg-white  text-slate-700  hover:bg-slate-100 "
            }`}
          >
            User Network Analysis
          </button>
          <button
            onClick={() => setActiveTab("rings")}
            className={`px-6 py-3 rounded-lg font-medium transition ${
              activeTab === "rings"
                ? "bg-blue-600 text-white"
                : "bg-white  text-slate-700  hover:bg-slate-100 "
            }`}
          >
            Fraud Ring Detection
          </button>
        </div>

        {/* User Network Analysis Tab */}
        {activeTab === "user" && (
          <div className="space-y-6">
            {/* Search Form */}
            <div className="bg-white  rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold text-slate-900  mb-4">
                Analyze User Network
              </h2>

              <div className="flex flex-col md:flex-row gap-4">
                <div className="flex-1">
                  <label className="block text-sm font-medium text-slate-700  mb-2">
                    User ID
                  </label>
                  <input
                    type="text"
                    value={userId}
                    onChange={(e) => setUserId(e.target.value)}
                    placeholder="Enter user ID..."
                    className="w-full px-4 py-2 border border-slate-300  rounded-lg bg-white  text-slate-900 "
                  />
                </div>

                <div className="w-32">
                  <label className="block text-sm font-medium text-slate-700  mb-2">
                    Depth
                  </label>
                  <select
                    value={depth}
                    onChange={(e) => setDepth(Number(e.target.value))}
                    className="w-full px-4 py-2 border border-slate-300  rounded-lg bg-white  text-slate-900 "
                  >
                    <option value={1}>1 hop</option>
                    <option value={2}>2 hops</option>
                    <option value={3}>3 hops</option>
                  </select>
                </div>

                <div className="w-32">
                  <label className="block text-sm font-medium text-slate-700  mb-2">
                    Days
                  </label>
                  <select
                    value={days}
                    onChange={(e) => setDays(Number(e.target.value))}
                    className="w-full px-4 py-2 border border-slate-300  rounded-lg bg-white  text-slate-900 "
                  >
                    <option value={30}>30 days</option>
                    <option value={60}>60 days</option>
                    <option value={90}>90 days</option>
                    <option value={180}>180 days</option>
                  </select>
                </div>

                <div className="flex items-end">
                  <button
                    onClick={analyzeUserNetwork}
                    disabled={loading || !userId}
                    className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
                  >
                    <Search className="h-4 w-4" />
                    Analyze
                  </button>
                </div>
              </div>
            </div>

            {/* Network Results */}
            {loading && (
              <div className="flex items-center justify-center py-12">
                <div className="text-center">
                  <Network className="h-12 w-12 animate-spin mx-auto mb-4 text-blue-600" />
                  <p className="text-lg text-slate-700 ">
                    Analyzing network...
                  </p>
                </div>
              </div>
            )}

            {networkData && !loading && (
              <div className="space-y-6">
                {/* Network Summary */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <MetricCard
                    title="Network Size"
                    value={networkData.network_size}
                    icon={<Users className="h-5 w-5" />}
                    color="blue"
                  />
                  <MetricCard
                    title="Connections"
                    value={networkData.connection_count}
                    icon={<Activity className="h-5 w-5" />}
                    color="green"
                  />
                  <MetricCard
                    title="Depth"
                    value={networkData.depth_analyzed}
                    icon={<Network className="h-5 w-5" />}
                    color="purple"
                  />
                  <MetricCard
                    title="Risk Score"
                    value={networkData.network_risk_score.toFixed(0)}
                    icon={<AlertTriangle className="h-5 w-5" />}
                    color={
                      networkData.network_risk_score >= 75
                        ? "red"
                        : networkData.network_risk_score >= 50
                          ? "orange"
                          : "green"
                    }
                  />
                </div>

                {/* Network Graph Visualization */}
                <div className="bg-white  rounded-lg shadow p-6">
                  <h3 className="text-lg font-semibold text-slate-900  mb-4">
                    Network Visualization
                  </h3>
                  <NetworkGraph
                    nodes={networkData.network.nodes.map((id) => {
                      const details = networkData.network.node_details[id];
                      return {
                        id,
                        type: details?.risk_level || "unknown",
                        transaction_count: details?.total_alerts || 0,
                        total_amount: 0,
                        risk_score: details?.risk_score,
                      };
                    })}
                    edges={networkData.network.edges.map((e) => ({
                      from: e.source,
                      to: e.target,
                      transaction_count: 1, // We don't have this aggregated in raw response
                      total_amount: e.amount,
                      latest_transaction: e.timestamp,
                    }))}
                  />
                </div>

                {/* Risk Indicators */}
                {(networkData.risk_indicators.circular_flows.length > 0 ||
                  Object.keys(
                    networkData.risk_indicators.shared_attributes || {},
                  ).length > 0 ||
                  networkData.risk_indicators.suspicious_clusters.length >
                    0) && (
                  <div className="bg-red-50  border border-red-200  rounded-lg p-6">
                    <h3 className="text-lg font-semibold text-red-900  mb-4">
                      Risk Indicators Detected
                    </h3>

                    <div className="space-y-4">
                      {networkData.risk_indicators.circular_flows.length >
                        0 && (
                        <div>
                          <p className="text-sm font-medium text-red-800  mb-2">
                            Circular Transaction Flows (
                            {networkData.risk_indicators.circular_flows.length})
                          </p>
                          <div className="space-y-2">
                            {networkData.risk_indicators.circular_flows.map(
                              (flow, idx: number) => (
                                <div
                                  key={idx}
                                  className="p-3 bg-white  rounded-lg"
                                >
                                  <p className="text-sm text-slate-900  font-mono">
                                    {flow.path.join(" → ")}
                                  </p>
                                  <p className="text-xs text-slate-600  mt-1">
                                    {flow.transaction_count} transactions,{" "}
                                    {flow.total_amount.toLocaleString()} EUR
                                  </p>
                                </div>
                              ),
                            )}
                          </div>
                        </div>
                      )}

                      {Object.keys(
                        networkData.risk_indicators.shared_attributes || {},
                      ).length > 0 && (
                        <div>
                          <p className="text-sm font-medium text-red-800  mb-2">
                            Shared Attributes
                          </p>
                          <div className="space-y-4">
                            {networkData.risk_indicators.shared_attributes
                              .shared_ips &&
                              Object.entries(
                                networkData.risk_indicators.shared_attributes
                                  .shared_ips,
                              ).map(([ip, users], idx) => (
                                <div
                                  key={`ip-${idx}`}
                                  className="p-3 bg-white  rounded-lg"
                                >
                                  <p className="text-sm text-slate-900 ">
                                    Shared IP:{" "}
                                    <span className="font-mono">{ip}</span>
                                  </p>
                                  <p className="text-xs text-slate-600  mt-1">
                                    Shared by: {users.join(", ")}
                                  </p>
                                </div>
                              ))}
                            {networkData.risk_indicators.shared_attributes
                              .shared_devices &&
                              Object.entries(
                                networkData.risk_indicators.shared_attributes
                                  .shared_devices,
                              ).map(([device, users], idx) => (
                                <div
                                  key={`dev-${idx}`}
                                  className="p-3 bg-white  rounded-lg"
                                >
                                  <p className="text-sm text-slate-900 ">
                                    Shared Device:{" "}
                                    <span className="font-mono text-[10px]">
                                      {device}
                                    </span>
                                  </p>
                                  <p className="text-xs text-slate-600  mt-1">
                                    Shared by: {users.join(", ")}
                                  </p>
                                </div>
                              ))}
                          </div>
                        </div>
                      )}

                      {networkData.risk_indicators.suspicious_clusters.length >
                        0 && (
                        <div>
                          <p className="text-sm font-medium text-red-800  mb-2">
                            Suspicious Clusters (
                            {
                              networkData.risk_indicators.suspicious_clusters
                                .length
                            }
                            )
                          </p>
                          <div className="space-y-2">
                            {networkData.risk_indicators.suspicious_clusters.map(
                              (cluster, idx: number) => (
                                <div
                                  key={idx}
                                  className="p-3 bg-white  rounded-lg"
                                >
                                  <p className="text-sm text-slate-900 ">
                                    Cluster of {cluster.member_count} users
                                  </p>
                                  <p className="text-xs text-slate-600  mt-1">
                                    Risk Score:{" "}
                                    {cluster.cluster_risk_score.toFixed(0)}
                                  </p>
                                </div>
                              ),
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Network Nodes */}
                <div className="bg-white  rounded-lg shadow p-6">
                  <h3 className="text-lg font-semibold text-slate-900  mb-4">
                    Network Nodes ({networkData.network.nodes.length})
                  </h3>

                  <div className="space-y-2">
                    {networkData.network.nodes.map((nodeId, idx) => {
                      const details = networkData.network.node_details[nodeId];
                      return (
                        <div
                          key={idx}
                          className="p-3 border border-slate-200  rounded-lg flex items-center justify-between"
                        >
                          <div>
                            <p className="text-sm font-mono text-slate-900 ">
                              {nodeId}
                            </p>
                            <p className="text-xs text-slate-600 ">
                              Risk Level: {details?.risk_level || "unknown"}
                            </p>
                          </div>
                          {details?.risk_score !== undefined && (
                            <span
                              className={`text-sm font-semibold ${
                                details.risk_score >= 75
                                  ? "text-red-600"
                                  : details.risk_score >= 50
                                    ? "text-orange-600"
                                    : "text-green-600"
                              }`}
                            >
                              Score: {details.risk_score.toFixed(0)}
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Fraud Ring Detection Tab */}
        {activeTab === "rings" && (
          <div className="space-y-6">
            <div className="bg-white  rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-slate-900 ">
                  Global Fraud Ring Detection
                </h2>
                <button
                  onClick={detectFraudRings}
                  disabled={loading}
                  className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition disabled:opacity-50"
                >
                  <AlertTriangle className="h-4 w-4" />
                  {loading ? "Scanning..." : "Scan for Fraud Rings"}
                </button>
              </div>

              <p className="text-sm text-slate-600 ">
                Detect organized fraud rings based on circular transaction
                flows, shared attributes, and suspicious clustering patterns.
              </p>
            </div>

            {loading && (
              <div className="flex items-center justify-center py-12">
                <div className="text-center">
                  <Network className="h-12 w-12 animate-spin mx-auto mb-4 text-red-600" />
                  <p className="text-lg text-slate-700 ">
                    Scanning for fraud rings...
                  </p>
                </div>
              </div>
            )}

            {fraudRings.length > 0 && !loading && (
              <div className="space-y-4">
                {fraudRings.map((ring) => (
                  <div
                    key={ring.ring_id}
                    className="bg-white  rounded-lg shadow p-6 border-l-4 border-red-500"
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <h3 className="text-lg font-semibold text-slate-900 ">
                          {ring.ring_id}
                        </h3>
                        <p className="text-sm text-slate-600 ">
                          {ring.size} members
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-2xl font-bold text-red-600">
                          {ring.risk_score.toFixed(0)}
                        </p>
                        <p className="text-xs text-slate-500 ">Risk Score</p>
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-4 mb-4">
                      <div>
                        <p className="text-xs text-slate-600  mb-1">Members</p>
                        <p className="text-sm font-semibold text-slate-900 ">
                          {ring.members.length}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-slate-600  mb-1">
                          Transactions
                        </p>
                        <p className="text-sm font-semibold text-slate-900 ">
                          {ring.transaction_count}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-slate-600  mb-1">
                          Total Volume
                        </p>
                        <p className="text-sm font-semibold text-slate-900 ">
                          {ring.total_volume.toLocaleString()}
                        </p>
                      </div>
                    </div>

                    <div className="mb-4">
                      <p className="text-xs text-slate-600  mb-2">Members</p>
                      <div className="flex flex-wrap gap-2">
                        {ring.members.map((member, idx) => (
                          <span
                            key={idx}
                            className="px-3 py-1 bg-slate-100  text-slate-900  text-xs font-mono rounded-full"
                          >
                            {member}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div>
                      <p className="text-xs text-slate-600  mb-2">
                        Risk Indicators
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {ring.indicators.map((indicator, idx) => (
                          <span
                            key={idx}
                            className="px-3 py-1 bg-red-100  text-red-800  text-xs rounded-full"
                          >
                            {indicator}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {fraudRings.length === 0 && !loading && (
              <div className="bg-white  rounded-lg shadow p-12 text-center">
                <Network className="h-16 w-16 mx-auto mb-4 text-green-500" />
                <p className="text-xl font-semibold text-slate-900  mb-2">
                  No fraud rings detected
                </p>
                <p className="text-slate-600 ">
                  Click &quot;Scan for Fraud Rings&quot; to run a global
                  analysis
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function MetricCard({
  title,
  value,
  icon,
  color,
}: {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  color: "blue" | "green" | "purple" | "orange" | "red";
}) {
  const colorClasses = {
    blue: "text-blue-600 bg-blue-50 ",
    green: "text-green-600 bg-green-50 ",
    purple: "text-purple-600 bg-purple-50 ",
    orange: "text-orange-600 bg-orange-50 ",
    red: "text-red-600 bg-red-50 ",
  };

  return (
    <div className="bg-white  rounded-lg shadow p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-600  mb-1">{title}</p>
          <p className="text-2xl font-bold text-slate-900 ">{value}</p>
        </div>
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>{icon}</div>
      </div>
    </div>
  );
}
