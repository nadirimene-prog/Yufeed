"use client";

import React, { useState } from "react";
import { Bell, X, ExternalLink } from "lucide-react";
import { useOptionalWebSocket } from "./WebSocketProvider";
import { cn } from "@/lib/utils";
import { formatDistanceToNow } from "date-fns";

/**
 * Notification Bell Component
 * Phase 4B: Task 6.3 - Frontend WebSocket Integration
 *
 * Displays notification count and panel with real-time updates
 */

export function NotificationBell() {
  const websocket = useOptionalWebSocket();
  const [isOpen, setIsOpen] = useState(false);

  if (!websocket) {
    return null; // Don't show if WebSocket is not available
  }

  const { notifications, isConnected, clearNotifications } = websocket;
  const unreadCount = notifications.length;

  const getPriorityColor = (priority?: string) => {
    switch (priority) {
      case "critical":
        return "border-l-red-500 bg-red-50";
      case "high":
        return "border-l-orange-500 bg-orange-50";
      case "medium":
        return "border-l-yellow-500 bg-yellow-50";
      case "low":
      default:
        return "border-l-blue-500 bg-blue-50";
    }
  };

  const getEventTypeIcon = (eventType: string) => {
    if (eventType.includes("alert")) return "🚨";
    if (eventType.includes("case")) return "📋";
    if (eventType.includes("decision")) return "⚖️";
    if (eventType.includes("system")) return "⚙️";
    return "📬";
  };

  return (
    <div className="relative">
      {/* Notification Bell Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "relative p-2 rounded-lg hover:bg-gray-100 transition-colors",
          isConnected ? "text-gray-700" : "text-gray-400",
        )}
        title={isConnected ? "Notifications" : "Disconnected"}
      >
        <Bell className="h-5 w-5" />

        {/* Unread Badge */}
        {unreadCount > 0 && (
          <span className="absolute top-0 right-0 inline-flex items-center justify-center px-2 py-1 text-xs font-bold leading-none text-white transform translate-x-1/2 -translate-y-1/2 bg-red-500 rounded-full">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}

        {/* Connection Status Indicator */}
        <span
          className={cn(
            "absolute bottom-0 right-0 block h-2 w-2 rounded-full ring-2 ring-white",
            isConnected ? "bg-green-500" : "bg-gray-400",
          )}
        />
      </button>

      {/* Notification Panel */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />

          {/* Panel */}
          <div className="absolute right-0 mt-2 w-96 max-h-[32rem] bg-white rounded-lg shadow-xl border border-gray-200 z-50 overflow-hidden flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-gray-50">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-semibold text-gray-900">
                  Notifications
                </h3>
                {unreadCount > 0 && (
                  <span className="px-2 py-0.5 text-xs font-medium bg-red-100 text-red-700 rounded-full">
                    {unreadCount}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                {notifications.length > 0 && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      clearNotifications();
                    }}
                    className="text-xs text-blue-600 hover:text-blue-700 font-medium"
                  >
                    Clear all
                  </button>
                )}
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-1 hover:bg-gray-200 rounded"
                >
                  <X className="h-4 w-4 text-gray-500" />
                </button>
              </div>
            </div>

            {/* Notifications List */}
            <div className="overflow-y-auto flex-1">
              {notifications.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 px-4">
                  <Bell className="h-12 w-12 text-gray-300 mb-3" />
                  <p className="text-sm text-gray-500 text-center">
                    No notifications yet
                  </p>
                  <p className="text-xs text-gray-400 text-center mt-1">
                    {isConnected
                      ? "You'll be notified when new events occur"
                      : "Connecting to notification service..."}
                  </p>
                </div>
              ) : (
                <ul className="divide-y divide-gray-100">
                  {notifications.map((notification, index) => (
                    <li
                      key={index}
                      className={cn(
                        "px-4 py-3 hover:bg-gray-50 transition-colors border-l-4",
                        getPriorityColor(notification.priority),
                      )}
                    >
                      <div className="flex items-start gap-3">
                        <span className="text-2xl flex-shrink-0">
                          {getEventTypeIcon(notification.event_type)}
                        </span>
                        <div className="flex-1 min-w-0">
                          {notification.title && (
                            <p className="text-sm font-semibold text-gray-900 mb-1">
                              {notification.title}
                            </p>
                          )}
                          <p className="text-sm text-gray-700 mb-1">
                            {notification.message}
                          </p>
                          <div className="flex items-center justify-between mt-2">
                            <p className="text-xs text-gray-500">
                              {formatDistanceToNow(
                                new Date(notification.timestamp),
                                { addSuffix: true },
                              )}
                            </p>
                            {notification.link && (
                              <a
                                href={notification.link}
                                className="text-xs text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1"
                                onClick={() => setIsOpen(false)}
                              >
                                View
                                <ExternalLink className="h-3 w-3" />
                              </a>
                            )}
                          </div>
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Footer */}
            {notifications.length > 0 && (
              <div className="px-4 py-2 border-t border-gray-200 bg-gray-50">
                <p className="text-xs text-gray-500 text-center">
                  Showing last {notifications.length} notification
                  {notifications.length !== 1 ? "s" : ""}
                </p>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
