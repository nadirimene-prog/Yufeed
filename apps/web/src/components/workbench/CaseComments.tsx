"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { MessageSquareReply, Send } from "lucide-react";
import { Button } from "@/components/ui/button-horizon";
import { useWorkspaceUsers } from "@/hooks/queries/useSpecializedData";
import apiClient from "@/lib/http";

export interface CaseComment {
  id: number;
  case_id: string;
  author_id: string;
  author_email: string;
  content: string;
  note_type: string;
  parent_comment_id?: number | null;
  mentions?: string[];
  created_at: string;
}

interface CaseCommentsProps {
  caseId: string;
  className?: string;
}

function queryKey(caseId: string) {
  return ["case-comments", caseId] as const;
}

export function CaseComments({ caseId, className }: CaseCommentsProps) {
  const queryClient = useQueryClient();
  const workspaceUsersQuery = useWorkspaceUsers();
  const [content, setContent] = useState("");
  const [replyToId, setReplyToId] = useState<number | null>(null);

  const commentsQuery = useQuery({
    queryKey: queryKey(caseId),
    queryFn: async () => {
      const response = await apiClient.get<CaseComment[]>(
        `/api/cases/${encodeURIComponent(caseId)}/comments`,
      );
      return response.data ?? [];
    },
  });

  const createComment = useMutation({
    mutationFn: async (payload: {
      content: string;
      parent_comment_id?: number;
      mentions?: string[];
    }) => {
      const response = await apiClient.post<CaseComment>(
        `/api/cases/${encodeURIComponent(caseId)}/comments`,
        payload,
      );
      return response.data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKey(caseId) });
      setContent("");
      setReplyToId(null);
    },
  });

  const byParent = useMemo(() => {
    const map = new Map<number | null, CaseComment[]>();
    for (const comment of commentsQuery.data ?? []) {
      const parent = comment.parent_comment_id ?? null;
      if (!map.has(parent)) map.set(parent, []);
      map.get(parent)?.push(comment);
    }
    return map;
  }, [commentsQuery.data]);

  const roots = byParent.get(null) ?? [];

  const submitComment = () => {
    const trimmed = content.trim();
    if (!trimmed) return;

    const mentions = Array.from(
      new Set(
        Array.from(trimmed.matchAll(/@([a-zA-Z0-9._-]+)/g)).map(
          (match) => match[1],
        ),
      ),
    );

    createComment.mutate({
      content: trimmed,
      ...(replyToId ? { parent_comment_id: replyToId } : {}),
      ...(mentions.length > 0 ? { mentions } : {}),
    });
  };

  return (
    <section className={className}>
      <div className="mb-3 rounded-xl border border-white/10 bg-white/5 p-3">
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-white/70">
          Collaboration Thread
        </h3>

        {replyToId ? (
          <div className="mb-2 flex items-center justify-between rounded-lg border border-aurora-500/30 bg-aurora-500/10 px-2 py-1 text-[11px] text-aurora-300">
            <span>Replying to comment #{replyToId}</span>
            <button
              type="button"
              onClick={() => setReplyToId(null)}
              className="underline"
            >
              Cancel
            </button>
          </div>
        ) : null}

        <textarea
          value={content}
          onChange={(event) => setContent(event.target.value)}
          placeholder="Write a comment... Use @user_id to mention analysts."
          className="h-24 w-full rounded-lg border border-white/10 bg-black/20 p-2 text-xs text-white placeholder:text-white/40"
        />

        <div className="mt-2 grid gap-2 sm:grid-cols-[1fr_auto]">
          <input
            list="workspace-comment-mentions"
            className="h-9 rounded-lg border border-white/10 bg-black/20 px-2 text-xs text-white placeholder:text-white/40"
            placeholder="Mention helper: start typing @user_id in the comment"
            disabled
            aria-label="Mentions helper"
          />
          <datalist id="workspace-comment-mentions">
            {(workspaceUsersQuery.data ?? []).map((user) => (
              <option key={user.user_id} value={`@${user.user_id}`}>
                {user.user_id}
              </option>
            ))}
          </datalist>
          <Button
            variant="glass"
            size="sm"
            loading={createComment.isPending}
            onClick={submitComment}
          >
            <Send className="h-3.5 w-3.5" />
            Send
          </Button>
        </div>
      </div>

      <div className="space-y-2">
        {(commentsQuery.data ?? []).length === 0 ? (
          <div className="rounded-xl border border-white/10 bg-white/5 p-3 text-xs text-white/60">
            No comments yet.
          </div>
        ) : null}

        {roots.map((root) => {
          const replies = byParent.get(root.id) ?? [];
          return (
            <article
              key={root.id}
              className="rounded-xl border border-white/10 bg-white/5 p-3"
            >
              <header className="mb-1 flex items-center justify-between gap-2 text-[11px] text-white/60">
                <span>{root.author_id || root.author_email}</span>
                <span>{new Date(root.created_at).toLocaleString()}</span>
              </header>
              <p className="whitespace-pre-wrap text-xs text-white/85">
                {root.content}
              </p>
              {(root.mentions ?? []).length > 0 ? (
                <p className="mt-1 text-[11px] text-aurora-300">
                  Mentions: {(root.mentions ?? []).join(", ")}
                </p>
              ) : null}
              <div className="mt-2">
                <button
                  type="button"
                  onClick={() => setReplyToId(root.id)}
                  className="inline-flex items-center gap-1 text-[11px] text-foreground-secondary hover:text-foreground"
                >
                  <MessageSquareReply className="h-3.5 w-3.5" />
                  Reply
                </button>
              </div>

              {replies.length > 0 ? (
                <div className="mt-3 space-y-2 border-l border-white/10 pl-3">
                  {replies.map((reply) => (
                    <div
                      key={reply.id}
                      className="rounded-lg border border-white/10 bg-black/20 p-2"
                    >
                      <header className="mb-1 flex items-center justify-between gap-2 text-[11px] text-white/60">
                        <span>{reply.author_id || reply.author_email}</span>
                        <span>
                          {new Date(reply.created_at).toLocaleString()}
                        </span>
                      </header>
                      <p className="whitespace-pre-wrap text-xs text-white/85">
                        {reply.content}
                      </p>
                    </div>
                  ))}
                </div>
              ) : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}

export default CaseComments;
