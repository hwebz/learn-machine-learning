export type DepthMode = "standard" | "deep";

export interface SourceLink {
  title: string;
  url: string;
  domain?: string;
  snippet?: string;
}

export interface ClaimItem {
  claim: string;
  verdict?: "verified" | "supported" | "disputed";
  confidence?: number;
}

export interface DisagreementItem {
  topic: string;
  viewpoints: Record<string, string>;
}

export interface StepLog {
  id: string;
  timestamp: string;
  provider?: string;
  step?: string;
  message: string;
  status: "pending" | "running" | "completed" | "error";
  data?: any;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  authorName: string;
  authorAvatar?: string;
  content: string;
  timestamp: string;
  tokens?: number;
  latencySeconds?: number;
  depth?: DepthMode;
  provider?: string;
  providers?: string[];
  sources?: SourceLink[];
  claims?: ClaimItem[];
  disagreements?: DisagreementItem[];
  provider_runs?: Record<string, any>;
  factCheckStatus?: "verified" | "reviewing" | "unverified";
  steps?: StepLog[];
}

export interface ChatSession {
  id: string;
  title: string;
  pinned: boolean;
  createdAt: string;
  messages: Message[];
  selectedProviders: string[];
  selectedProvider?: string;
  depth: DepthMode;
  jobId?: string;
  status?: "queued" | "running" | "completed" | "partial" | "failed" | "cancelled";
}

export interface ProviderInfo {
  id: string;
  name: string;
  modelName: string;
  shortDesc: string;
  fullDesc: string;
  contextWindow: string;
  trainingData: string;
  category: "Thinking" | "General" | "Search" | "Enterprise";
  supportsDeepMode: boolean;
  deepModeLabel?: string;
  standardModeLabel?: string;
  color: string;
  avatarBg: string;
  iconType: string;
}
