'use client';

import { useEffect, useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import { motion } from 'framer-motion';

// Dynamically import ForceGraph2D to avoid SSR issues
const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false });

interface NetworkGraphProps {
  nodes: Array<{
    id: string;
    type: string;
    transaction_count: number;
    total_amount: number;
    risk_score?: number;
  }>;
  edges: Array<{
    from: string;
    to: string;
    transaction_count: number;
    total_amount: number;
  }>;
}

export default function NetworkGraph({ nodes, edges }: NetworkGraphProps) {
  const [graphData, setGraphData] = useState<any>(null);
  const fgRef = useRef<any>();

  useEffect(() => {
    if (!nodes || !edges) return;

    // Transform data for react-force-graph format
    const transformedData = {
      nodes: nodes.map(node => ({
        id: node.id,
        name: node.id,
        val: node.transaction_count,
        color: getNodeColor(node.risk_score),
        ...node
      })),
      links: edges.map(edge => ({
        source: edge.from,
        target: edge.to,
        value: edge.transaction_count,
        ...edge
      }))
    };

    setGraphData(transformedData);
  }, [nodes, edges]);

  const getNodeColor = (riskScore?: number) => {
    if (!riskScore) return '#3b82f6'; // blue
    if (riskScore >= 70) return '#dc2626'; // red
    if (riskScore >= 40) return '#ea580c'; // orange
    return '#10b981'; // green
  };

  if (!graphData) {
    return (
      <div className="flex items-center justify-center h-96">
        <p className="text-gray-500">Loading graph...</p>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="w-full h-96 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden"
    >
      <ForceGraph2D
        ref={fgRef}
        graphData={graphData}
        nodeLabel={(node: any) => `
          <div style="padding: 8px; background: rgba(0,0,0,0.8); color: white; border-radius: 4px; font-size: 12px;">
            <strong>${node.id}</strong><br/>
            Transactions: ${node.transaction_count}<br/>
            Amount: ${node.total_amount.toLocaleString()}<br/>
            ${node.risk_score ? `Risk: ${node.risk_score.toFixed(0)}` : ''}
          </div>
        `}
        linkLabel={(link: any) => `
          <div style="padding: 8px; background: rgba(0,0,0,0.8); color: white; border-radius: 4px; font-size: 12px;">
            ${link.source.id} → ${link.target.id}<br/>
            Transactions: ${link.transaction_count}<br/>
            Amount: ${link.total_amount.toLocaleString()}
          </div>
        `}
        nodeRelSize={6}
        nodeCanvasObject={(node: any, ctx, globalScale) => {
          const label = node.id;
          const fontSize = 12 / globalScale;
          ctx.font = `${fontSize}px Sans-Serif`;
          const textWidth = ctx.measureText(label).width;
          const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.2);

          // Draw node circle
          ctx.beginPath();
          ctx.arc(node.x, node.y, node.val || 5, 0, 2 * Math.PI, false);
          ctx.fillStyle = node.color;
          ctx.fill();

          // Draw label background
          ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
          ctx.fillRect(
            node.x - bckgDimensions[0] / 2,
            node.y + 8,
            bckgDimensions[0],
            bckgDimensions[1]
          );

          // Draw label text
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillStyle = '#ffffff';
          ctx.fillText(label, node.x, node.y + 8 + bckgDimensions[1] / 2);
        }}
        linkColor={() => '#6b7280'}
        linkWidth={(link: any) => Math.sqrt(link.value)}
        linkDirectionalArrowLength={3}
        linkDirectionalArrowRelPos={1}
        linkCurvature={0.25}
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.3}
        cooldownTicks={100}
        onNodeClick={(node: any) => {
          console.log('Node clicked:', node);
        }}
      />

      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
        <p className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">Risk Levels</p>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-red-600"></div>
            <span className="text-xs text-gray-600 dark:text-gray-400">High Risk (70+)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-orange-600"></div>
            <span className="text-xs text-gray-600 dark:text-gray-400">Medium Risk (40-70)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-green-600"></div>
            <span className="text-xs text-gray-600 dark:text-gray-400">Low Risk (&lt;40)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-blue-600"></div>
            <span className="text-xs text-gray-600 dark:text-gray-400">Unknown</span>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
