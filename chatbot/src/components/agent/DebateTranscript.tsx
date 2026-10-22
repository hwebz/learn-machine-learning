import React, { useState } from "react";
import { DebateEntry } from "../../types/chat";
import { CopyIcon, CheckIcon, ChevronDownIcon, ChevronRightIcon } from "../icons/Icons";

export interface DebateTranscriptProps {
  transcript?: DebateEntry[];
  compact?: boolean;
  defaultExpanded?: boolean;
}

export const DebateTranscript: React.FC<DebateTranscriptProps> = ({
  transcript,
  compact = false,
  defaultExpanded = true,
}) => {
  const [expandedRounds, setExpandedRounds] = useState<Record<number, boolean>>(() => {
    return { 1: defaultExpanded, 2: defaultExpanded, 3: defaultExpanded, 4: defaultExpanded, 5: defaultExpanded };
  });
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [copiedAll, setCopiedAll] = useState(false);

  if (!transcript || transcript.length === 0) {
    return null;
  }

  // Group entries by round number
  const roundsMap: Record<number, DebateEntry[]> = {};
  for (const entry of transcript) {
    const r = entry.round || 1;
    if (!roundsMap[r]) {
      roundsMap[r] = [];
    }
    roundsMap[r].push(entry);
  }
  const roundNumbers = Object.keys(roundsMap)
    .map(Number)
    .sort((a, b) => a - b);

  const totalCritiques = transcript.filter((t) => t.side === "red_team").length;
  const totalDefenses = transcript.filter((t) => t.side === "defender").length;

  const toggleRound = (round: number) => {
    setExpandedRounds((prev) => ({ ...prev, [round]: !prev[round] }));
  };

  const copyText = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 1800);
  };

  const copyEntireDebate = () => {
    const formatted = transcript
      .map(
        (t) =>
          `[VÒNG ${t.round} - ${t.side === "red_team" ? "RED TEAM (Phản biện)" : "DEFENDER (Bảo vệ)"} (${t.provider})]\n${t.content || t.error || ""}\n`
      )
      .join("\n---\n\n");
    navigator.clipboard.writeText(formatted);
    setCopiedAll(true);
    setTimeout(() => setCopiedAll(false), 2000);
  };

  return (
    <div
      className={`rounded-xl border transition-all duration-300 ${
        compact
          ? "bg-slate-900/60 border-slate-800/80 p-3"
          : "bg-gradient-to-b from-slate-900/90 to-slate-950/90 border-slate-800/90 shadow-xl backdrop-blur-md p-4 sm:p-5"
      }`}
    >
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3.5 border-b border-slate-800/80">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-rose-500/20 to-amber-500/20 border border-rose-500/30 flex items-center justify-center text-rose-400">
            <span style={{ fontSize: 16 }}>⚔️</span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-1.5">
                Vòng tranh luận phản biện
                <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-300 border border-rose-500/20">
                  Adversarial Debate
                </span>
              </h3>
            </div>
            <p className="text-[11px] text-slate-400">
              {roundNumbers.length} vòng đấu • {totalCritiques} phản biện Red Team • {totalDefenses} luận điểm bảo vệ
            </p>
          </div>
        </div>

        <button
          onClick={copyEntireDebate}
          className="flex items-center gap-1.5 text-xs text-slate-300 hover:text-white bg-slate-800/70 hover:bg-slate-700/80 px-2.5 py-1.5 rounded-lg border border-slate-700/60 transition-colors"
          title="Sao chép toàn bộ biên bản tranh luận"
        >
          {copiedAll ? <CheckIcon size={14} color="#34d399" /> : <CopyIcon size={14} />}
          <span>{copiedAll ? "Đã chép" : "Sao chép biên bản"}</span>
        </button>
      </div>

      {/* Rounds List */}
      <div className="mt-3.5 space-y-4">
        {roundNumbers.map((roundNum) => {
          const entries = roundsMap[roundNum];
          const isExpanded = expandedRounds[roundNum] ?? defaultExpanded;

          return (
            <div
              key={roundNum}
              className="rounded-lg border border-slate-800/60 bg-slate-950/40 overflow-hidden"
            >
              {/* Round Toggle Bar */}
              <button
                type="button"
                onClick={() => toggleRound(roundNum)}
                className="w-full flex items-center justify-between px-3.5 py-2.5 bg-slate-900/50 hover:bg-slate-850/60 text-left transition-colors cursor-pointer"
              >
                <div className="flex items-center gap-2">
                  {isExpanded ? (
                    <ChevronDownIcon size={15} color="#94a3b8" />
                  ) : (
                    <ChevronRightIcon size={15} color="#94a3b8" />
                  )}
                  <span className="text-xs font-semibold text-slate-200">
                    Vòng {roundNum} ({entries.length} lượt đối thoại)
                  </span>
                </div>
                <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
                  <span className="px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-300 border border-rose-500/20">
                    ⚔️ Red Team
                  </span>
                  <span className="text-slate-600">vs</span>
                  <span className="px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-300 border border-blue-500/20">
                    🛡️ Defender
                  </span>
                </div>
              </button>

              {/* Round Entries */}
              {isExpanded && (
                <div className="p-3 sm:p-4 space-y-3.5 border-t border-slate-800/60">
                  {entries.map((entry, idx) => {
                    const isRed = entry.side === "red_team";
                    const globalIdx = roundNum * 10 + idx;

                    return (
                      <div
                        key={idx}
                        className={`rounded-lg p-3.5 border transition-all ${
                          isRed
                            ? "bg-rose-950/15 border-rose-800/30 hover:border-rose-700/40"
                            : "bg-blue-950/15 border-blue-800/30 hover:border-blue-700/40"
                        }`}
                      >
                        {/* Entry Header */}
                        <div className="flex items-center justify-between gap-2 mb-2">
                          <div className="flex items-center gap-2">
                            <span
                              className={`flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full ${
                                isRed
                                  ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                                  : "bg-blue-500/20 text-blue-300 border border-blue-500/30"
                              }`}
                            >
                              {isRed ? (
                                <>
                                  <span>⚔️</span>
                                  Red Team Critique
                                </>
                              ) : (
                                <>
                                  <span>🛡️</span>
                                  Defender Rebuttal
                                </>
                              )}
                            </span>

                            <span className="text-xs font-mono font-medium text-slate-300 bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700/50">
                              {entry.provider}
                            </span>

                            {entry.elapsed_s !== undefined && (
                              <span className="text-[10px] text-slate-400 font-mono">
                                ⏱️ {entry.elapsed_s}s
                              </span>
                            )}
                          </div>

                          {entry.content && (
                            <button
                              onClick={() => copyText(entry.content || "", globalIdx)}
                              className="text-slate-400 hover:text-slate-200 p-1 rounded hover:bg-slate-800/60 transition-colors"
                              title="Sao chép phản hồi này"
                            >
                              {copiedIndex === globalIdx ? (
                                <CheckIcon size={14} color="#34d399" />
                              ) : (
                                <CopyIcon size={14} />
                              )}
                            </button>
                          )}
                        </div>

                        {/* Entry Content */}
                        {entry.error ? (
                          <div className="text-xs text-rose-400 bg-rose-950/30 p-2.5 rounded border border-rose-800/40">
                            ⚠️ Vòng tranh luận gặp sự cố: {entry.error}
                          </div>
                        ) : (
                          <div className="text-xs sm:text-[13px] text-slate-200 leading-relaxed whitespace-pre-wrap font-sans">
                            {entry.content}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
