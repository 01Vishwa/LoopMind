"use client";

import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X, ChevronDown, ChevronUp } from "lucide-react";
import { StatusBadge } from "@/components/shared/StatusBadge";

export interface SubQuestion {
  index: number;
  text: string;
  code?: string;
  output?: string;
  status: "resolved" | "unresolved";
}

export interface CitationPopoverProps {
  subQuestion: SubQuestion;
  onClose: () => void;
  anchorRect?: DOMRect;
}

export function CitationPopover({ subQuestion, onClose }: CitationPopoverProps) {
  const [codeExpanded, setCodeExpanded] = useState(false);

  // Radix Dialog provides focus trap, initial focus, focus restoration, scroll
  // lock and Escape-to-dismiss (spec §4.5 / §6.8).
  return (
    <Dialog.Root open onOpenChange={(next) => { if (!next) onClose(); }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40" />
        <Dialog.Content
          aria-describedby={undefined}
          className="fixed right-4 top-1/4 z-50 w-full max-w-md bg-vera-surface border border-vera-border rounded shadow-lg"
          style={{ borderRadius: "6px" }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-vera-border">
            <div className="flex items-center gap-2">
              <span className="text-mono-ui text-vera-accent font-medium">SQ-{subQuestion.index}</span>
              <StatusBadge status={subQuestion.status === "resolved" ? "sufficient" : "insufficient"} />
            </div>
            <Dialog.Title className="sr-only">
              Sub-question {subQuestion.index} detail
            </Dialog.Title>
            <Dialog.Close aria-label="Close" className="text-vera-muted hover:text-vera-ink">
              <X size={16} strokeWidth={1.5} />
            </Dialog.Close>
          </div>

          <div className="px-4 py-4 space-y-4">
            {/* Sub-question text */}
            <p className="text-body text-vera-ink">{subQuestion.text}</p>

            {/* Collapsible code */}
            <div>
              <button
                onClick={() => setCodeExpanded((v) => !v)}
                className="flex items-center gap-1.5 text-label text-vera-muted hover:text-vera-ink transition-colors mb-2"
                aria-expanded={codeExpanded}
              >
                {codeExpanded ? <ChevronUp size={12} strokeWidth={1.5} /> : <ChevronDown size={12} strokeWidth={1.5} />}
                Code
              </button>
              {codeExpanded && (
                <pre
                  className="text-code text-vera-code-fg bg-vera-code-bg rounded p-3 overflow-x-auto"
                  style={{ fontSize: "12px", borderRadius: "4px" }}
                >
                  {subQuestion.code ?? ""}
                </pre>
              )}
            </div>

            {/* Output */}
            {subQuestion.output && (
              <div>
                <p className="text-label text-vera-muted mb-2">Output</p>
                <pre
                  className="text-code text-vera-code-fg bg-vera-code-bg rounded p-3 overflow-x-auto"
                  style={{ fontSize: "12px", borderRadius: "4px", maxHeight: "120px" }}
                >
                  {subQuestion.output}
                </pre>
              </div>
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
