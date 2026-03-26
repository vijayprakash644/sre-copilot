"use client";

import { useEffect, useState } from "react";
import { RunbookUpload } from "@/components/dashboard/runbook-upload";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Trash2, FileText, Calendar } from "lucide-react";

interface Runbook {
  id: string;
  filename: string;
  content_type: string;
  chunk_count: number;
  ingested_at: string;
}

export default function RunbooksPage() {
  const [runbooks, setRunbooks] = useState<Runbook[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<string | null>(null);

  async function fetchRunbooks() {
    try {
      const res = await fetch("/api/proxy/api/runbooks");
      if (res.ok) {
        setRunbooks(await res.json());
      }
    } catch (err) {
      console.error("Failed to fetch runbooks:", err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchRunbooks();
  }, []);

  async function handleDelete(id: string, filename: string) {
    if (!confirm(`Delete "${filename}"?`)) return;
    setDeleting(id);
    try {
      const res = await fetch(`/api/proxy/api/runbooks/${id}`, { method: "DELETE" });
      if (res.ok) {
        setRunbooks((prev) => prev.filter((r) => r.id !== id));
      }
    } catch (err) {
      console.error("Delete failed:", err);
    } finally {
      setDeleting(null);
    }
  }

  return (
    <div className="p-8 max-w-4xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white mb-1">Runbooks</h1>
        <p className="text-slate-400 text-sm">
          Upload runbooks (Markdown or PDF) to improve triage accuracy. SRE Copilot
          retrieves relevant sections automatically for each alert.
        </p>
      </div>

      <RunbookUpload onUploaded={fetchRunbooks} />

      <div className="mt-8">
        <h2 className="text-lg font-semibold text-white mb-4">
          Ingested Runbooks{" "}
          {!loading && (
            <span className="text-slate-400 font-normal text-sm">
              ({runbooks.length})
            </span>
          )}
        </h2>

        {loading ? (
          <div className="text-slate-400 text-sm">Loading...</div>
        ) : runbooks.length === 0 ? (
          <Card className="bg-slate-800 border-slate-700">
            <CardContent className="py-12 text-center">
              <FileText className="w-10 h-10 text-slate-600 mx-auto mb-3" />
              <p className="text-slate-400 text-sm">
                No runbooks ingested yet. Upload your first one above.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {runbooks.map((rb) => (
              <Card key={rb.id} className="bg-slate-800 border-slate-700">
                <CardContent className="py-4 px-5 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <FileText className="w-5 h-5 text-slate-400 flex-shrink-0" />
                    <div>
                      <p className="text-white text-sm font-medium">{rb.filename}</p>
                      <div className="flex items-center gap-3 mt-1">
                        <Badge
                          variant="secondary"
                          className="text-xs bg-slate-700 text-slate-300"
                        >
                          {rb.content_type}
                        </Badge>
                        <span className="text-slate-500 text-xs">
                          {rb.chunk_count} chunks
                        </span>
                        <span className="text-slate-500 text-xs flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          {new Date(rb.ingested_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-slate-400 hover:text-red-400 hover:bg-red-400/10"
                    disabled={deleting === rb.id}
                    onClick={() => handleDelete(rb.id, rb.filename)}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
