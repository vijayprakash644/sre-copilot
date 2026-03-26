"use client";

import React, { useCallback, useRef, useState } from "react";
import {
  Upload,
  FileText,
  Trash2,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  BookOpen,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  uploadRunbook,
  deleteRunbook,
  type Runbook,
  type UploadRunbookResponse,
} from "@/lib/api";
import { cn, formatDateTime } from "@/lib/utils";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface UploadState {
  file: File;
  status: "uploading" | "done" | "error";
  error?: string;
  result?: UploadRunbookResponse;
}

interface RunbookUploadProps {
  runbooks: Runbook[];
  onRunbookDeleted: (id: string) => void;
  onRunbookUploaded: (runbook: UploadRunbookResponse) => void;
}

export function RunbookUpload({
  runbooks,
  onRunbookDeleted,
  onRunbookUploaded,
}: RunbookUploadProps) {
  const [dragOver, setDragOver] = useState(false);
  const [uploads, setUploads] = useState<UploadState[]>([]);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const processFiles = useCallback(
    async (files: FileList | File[]) => {
      const fileArr = Array.from(files).filter((f) =>
        [
          "application/pdf",
          "text/markdown",
          "text/plain",
          "text/x-markdown",
        ].includes(f.type) || f.name.endsWith(".md") || f.name.endsWith(".txt") || f.name.endsWith(".pdf")
      );

      if (fileArr.length === 0) return;

      const newUploads: UploadState[] = fileArr.map((f) => ({
        file: f,
        status: "uploading",
      }));

      setUploads((prev) => [...newUploads, ...prev]);

      await Promise.all(
        fileArr.map(async (file, i) => {
          try {
            const result = await uploadRunbook(file);
            setUploads((prev) =>
              prev.map((u, j) =>
                j === i ? { ...u, status: "done", result } : u
              )
            );
            onRunbookUploaded(result);
          } catch (e) {
            setUploads((prev) =>
              prev.map((u, j) =>
                j === i
                  ? { ...u, status: "error", error: (e as Error).message }
                  : u
              )
            );
          }
        })
      );
    },
    [onRunbookUploaded]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      processFiles(e.dataTransfer.files);
    },
    [processFiles]
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files) {
        processFiles(e.target.files);
        e.target.value = "";
      }
    },
    [processFiles]
  );

  const handleDelete = useCallback(
    async (id: string) => {
      setDeletingId(id);
      try {
        await deleteRunbook(id);
        onRunbookDeleted(id);
      } catch {
        // TODO: show toast
      } finally {
        setDeletingId(null);
      }
    },
    [onRunbookDeleted]
  );

  return (
    <div className="space-y-6">
      {/* Drop zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={cn(
          "relative rounded-2xl border-2 border-dashed p-12 text-center cursor-pointer transition-all duration-200",
          dragOver
            ? "border-blue-500/60 bg-blue-950/20 scale-[1.01]"
            : "border-white/10 hover:border-white/20 hover:bg-white/[0.02]"
        )}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.md,.txt,text/markdown,text/plain,application/pdf"
          multiple
          onChange={handleFileInput}
          className="sr-only"
        />

        <div
          className={cn(
            "w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4 transition-colors",
            dragOver
              ? "bg-blue-600/30"
              : "bg-white/5"
          )}
        >
          <Upload
            className={cn(
              "w-7 h-7 transition-colors",
              dragOver ? "text-blue-400" : "text-gray-500"
            )}
          />
        </div>

        <p className="text-sm font-medium text-white mb-1">
          {dragOver ? "Drop your runbooks here" : "Drag & drop runbooks here"}
        </p>
        <p className="text-xs text-gray-500 mb-4">
          Supports PDF, Markdown (.md), and plain text (.txt) — up to 50 MB each
        </p>
        <Button
          variant="outline"
          size="sm"
          className="border-white/20 text-gray-300 hover:text-white pointer-events-none"
        >
          Choose files
        </Button>
      </div>

      {/* In-progress uploads */}
      {uploads.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">
            Recent uploads
          </p>
          {uploads.map((u, i) => (
            <div
              key={i}
              className={cn(
                "flex items-center gap-3 rounded-lg border px-4 py-3 text-sm",
                u.status === "done"
                  ? "border-green-500/20 bg-green-950/10"
                  : u.status === "error"
                  ? "border-red-500/20 bg-red-950/10"
                  : "border-white/10 bg-white/[0.02]"
              )}
            >
              <FileText
                className={cn(
                  "w-4 h-4 flex-shrink-0",
                  u.status === "done"
                    ? "text-green-400"
                    : u.status === "error"
                    ? "text-red-400"
                    : "text-gray-500"
                )}
              />
              <span className="flex-1 truncate text-gray-300">{u.file.name}</span>
              <span className="text-xs text-gray-600 flex-shrink-0">
                {formatBytes(u.file.size)}
              </span>
              {u.status === "uploading" && (
                <Loader2 className="w-4 h-4 text-blue-400 animate-spin flex-shrink-0" />
              )}
              {u.status === "done" && (
                <CheckCircle2 className="w-4 h-4 text-green-400 flex-shrink-0" />
              )}
              {u.status === "error" && (
                <AlertTriangle
                  className="w-4 h-4 text-red-400 flex-shrink-0"
                  title={u.error}
                />
              )}
            </div>
          ))}
        </div>
      )}

      {/* Existing runbooks */}
      <div className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">
          Ingested runbooks ({runbooks.length})
        </p>

        {runbooks.length === 0 && (
          <div className="rounded-xl border border-white/5 bg-white/[0.02] p-8 text-center">
            <BookOpen className="w-8 h-8 text-gray-700 mx-auto mb-3" />
            <p className="text-sm text-gray-500">
              No runbooks yet. Upload your first runbook above.
            </p>
          </div>
        )}

        {runbooks.map((rb) => (
          <div
            key={rb.id}
            className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/[0.02] px-4 py-3 hover:bg-white/[0.04] transition-colors group"
          >
            <div className="w-9 h-9 rounded-lg bg-white/5 flex items-center justify-center flex-shrink-0">
              <FileText className="w-4 h-4 text-blue-400" />
            </div>

            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">{rb.filename}</p>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-xs text-gray-500">
                  {rb.chunk_count} chunks
                </span>
                <span className="text-gray-700">·</span>
                <span className="text-xs text-gray-500">{formatBytes(rb.size_bytes)}</span>
                <span className="text-gray-700">·</span>
                <span className="text-xs text-gray-500">
                  {formatDateTime(rb.uploaded_at)}
                </span>
              </div>
            </div>

            <Button
              variant="ghost"
              size="icon"
              className="text-gray-600 hover:text-red-400 hover:bg-red-500/10 opacity-0 group-hover:opacity-100 transition-all flex-shrink-0"
              onClick={() => handleDelete(rb.id)}
              disabled={deletingId === rb.id}
              aria-label={`Delete ${rb.filename}`}
            >
              {deletingId === rb.id ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Trash2 className="w-4 h-4" />
              )}
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}
