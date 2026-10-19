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

export interface ThinkingStep {
  title: string;
  description?: string;
  status?: "running" | "completed" | "pending";
  options?: Record<string, any>;
}

export interface StepLog {
  id: string;
  timestamp: string;
  provider?: string;
  step?: string;
  message: string;
  status: "pending" | "running" | "completed" | "error" | "orchestrating" | "researching" | "leading";
  data?: any;
  thinkingText?: string;
  thinkingSteps?: ThinkingStep[];
  citations?: SourceLink[];
  isThinking?: boolean;
  streamingText?: string;
  conversationUrl?: string;
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
  provider_runs?: Record<string, any> | any[];
  provider_options?: Record<string, any>;
  factCheckStatus?: "verified" | "reviewing" | "unverified";
  steps?: StepLog[];
  job_type?: "research" | "agent";
  orchestrator_provider?: string;
  lead_provider?: string;
  tone?: string;
  orchestrator_dispatch?: AgentDispatchPlanItem[];
  delegated_providers?: string[];
  orchestrator_conversation_url?: string;
  lead_conversation_url?: string;
  provider_conversations?: Record<string, string>;
  jobId?: string;
}

export interface AgentDispatchPlanItem {
  id: string;
  name: string;
  config?: Record<string, any>;
  sub_topic: string;
  question: string;
  branch_index?: number;
  provider_role_key?: string;
  conversation_url?: string;
}

import { ProviderSelectionConfig } from "./capabilities";
export * from "./capabilities";

export interface ChatSession {
  id: string;
  title: string;
  pinned: boolean;
  createdAt: string;
  createdTimestamp?: number;
  messages: Message[];
  selectedProviders: string[];
  selectedProvider?: string;
  depth?: DepthMode;
  jobId?: string;
  status?: "queued" | "running" | "completed" | "partial" | "failed" | "cancelled" | "orchestrating" | "researching" | "leading";
  providerConfigurations?: Record<string, ProviderSelectionConfig>;
  job_type?: "research" | "agent";
  orchestrator_provider?: string;
  lead_provider?: string;
  tone?: string;
  orchestrator_dispatch?: AgentDispatchPlanItem[];
  delegated_providers?: string[];
  orchestrator_conversation_url?: string;
  lead_conversation_url?: string;
  provider_conversations?: Record<string, string>;
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
