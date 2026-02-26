"use client";

import React, { useState } from "react";
import { cn } from "@/lib/utils";
import {
  ChevronRight,
  ChevronDown,
  FolderOpen,
  Folder,
  AlertTriangle,
} from "lucide-react";
import type {
  RiskCategoryTree as RiskCategoryTreeType,
  RiskLevelType,
} from "@/types/compliance";

interface RiskCategoryTreeProps {
  categories: RiskCategoryTreeType[];
  selectedCategoryId?: number;
  onSelectCategory?: (category: RiskCategoryTreeType) => void;
  className?: string;
}

interface TreeNodeProps {
  category: RiskCategoryTreeType;
  level: number;
  selectedCategoryId?: number;
  onSelectCategory?: (category: RiskCategoryTreeType) => void;
}

const getRiskLevelColor = (level: RiskLevelType): string => {
  switch (level) {
    case "critical":
      return "text-red-400";
    case "high":
      return "text-orange-400";
    case "medium":
      return "text-yellow-400";
    case "low":
      return "text-green-400";
  }
};

const getRiskLevelBgColor = (level: RiskLevelType): string => {
  switch (level) {
    case "critical":
      return "bg-red-500/20";
    case "high":
      return "bg-orange-500/20";
    case "medium":
      return "bg-yellow-500/20";
    case "low":
      return "bg-green-500/20";
  }
};

function TreeNode({
  category,
  level,
  selectedCategoryId,
  onSelectCategory,
}: TreeNodeProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const hasChildren = category.children && category.children.length > 0;
  const isSelected = selectedCategoryId === category.id;

  return (
    <div>
      <div
        className={cn(
          "flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-pointer transition-all",
          isSelected
            ? "bg-[#0052ff]/20 text-white"
            : "text-white/70 hover:bg-white/5 hover:text-white",
        )}
        style={{ paddingLeft: `${level * 12 + 8}px` }}
        onClick={() => onSelectCategory?.(category)}
      >
        {/* Expand/Collapse Button */}
        {hasChildren ? (
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsExpanded(!isExpanded);
            }}
            className="p-0.5 rounded hover:bg-white/10"
          >
            {isExpanded ? (
              <ChevronDown className="h-4 w-4 text-white/50" />
            ) : (
              <ChevronRight className="h-4 w-4 text-white/50" />
            )}
          </button>
        ) : (
          <span className="w-5" />
        )}

        {/* Icon */}
        {hasChildren ? (
          isExpanded ? (
            <FolderOpen className="h-4 w-4 text-sky-500" />
          ) : (
            <Folder className="h-4 w-4 text-sky-500" />
          )
        ) : (
          <AlertTriangle
            className={cn("h-4 w-4", getRiskLevelColor(category.risk_level))}
          />
        )}

        {/* Name */}
        <span className="flex-1 text-sm font-medium truncate">
          {category.name}
        </span>

        {/* Risk Level Badge */}
        <span
          className={cn(
            "text-xs px-1.5 py-0.5 rounded",
            getRiskLevelBgColor(category.risk_level),
            getRiskLevelColor(category.risk_level),
          )}
        >
          {category.risk_level}
        </span>

        {/* Entries Count */}
        {(category.entries_count ?? 0) > 0 && (
          <span className="text-xs text-white/40 bg-white/10 px-1.5 py-0.5 rounded">
            {category.entries_count}
          </span>
        )}
      </div>

      {/* Children */}
      {hasChildren && isExpanded && (
        <div>
          {category.children.map((child) => (
            <TreeNode
              key={child.id}
              category={child}
              level={level + 1}
              selectedCategoryId={selectedCategoryId}
              onSelectCategory={onSelectCategory}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function RiskCategoryTree({
  categories,
  selectedCategoryId,
  onSelectCategory,
  className,
}: RiskCategoryTreeProps) {
  if (categories.length === 0) {
    return (
      <div className={cn("p-4 text-center text-white/50 text-sm", className)}>
        No categories available
      </div>
    );
  }

  return (
    <div className={cn("space-y-1", className)}>
      {/* All Categories Option */}
      <div
        className={cn(
          "flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-pointer transition-all",
          !selectedCategoryId
            ? "bg-[#0052ff]/20 text-white"
            : "text-white/70 hover:bg-white/5 hover:text-white",
        )}
        onClick={() =>
          onSelectCategory?.(null as unknown as RiskCategoryTreeType)
        }
      >
        <span className="w-5" />
        <FolderOpen className="h-4 w-4 text-[#0052ff]" />
        <span className="flex-1 text-sm font-medium">All Categories</span>
      </div>

      {/* Category Tree */}
      {categories.map((category) => (
        <TreeNode
          key={category.id}
          category={category}
          level={0}
          selectedCategoryId={selectedCategoryId}
          onSelectCategory={onSelectCategory}
        />
      ))}
    </div>
  );
}
