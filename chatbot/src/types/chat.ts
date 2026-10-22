export type DepthMode = "standard" | "deep";

export interface SourceLink {
  title: string;
  url: string;
  domain?: string;
  snippet?: string;
}

export interface ClaimItem {
  id?: string;
  claim?: string;
  text?: string;
  verdict?: "verified" | "supported" | "single_source" | "unsupported" | "conflict" | "disputed";
  confidence?: number;
  reasoning?: string;
  branch?: string;
  provider?: string;
}

export interface DisagreementItem {
  topic: string;
  viewpoints: Record<string, string>;
}

export type ReportFormat = "narrative" | "matrix" | "hybrid";

export interface MatrixAlternative {
  name: string;
  description: string;
  scores: {
    cost: number;
    performance: number;
    complexity: number;
    maturity: number;
    scalability: number;
  };
  pros: string[];
  cons: string[];
}

export interface MatrixReport {
  title: string;
  executive_summary: string;
  alternatives: MatrixAlternative[];
  recommendation: string;
  caveats: string[];
  disagreements: string[];
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
  status: "pending" | "running" | "completed" | "error" | "orchestrating" | "researching" | "fact_checking" | "leading";
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
  enable_fact_check?: boolean;
  fact_check_provider?: string;
  fact_check_config?: Record<string, any>;
  fact_check_results?: ClaimItem[] | any[];
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
  summarization_provider?: string;
  summarization_config?: Record<string, any>;
  context_summary?: string;
  report_format?: string;
  report_matrix?: MatrixReport;
  auto_scale_agents?: boolean;
  min_agents?: number;
  max_agents?: number;
  complexity?: ComplexityAssessment;
  jobId?: string;
}

export interface ComplexityAssessment {
  complexity_level: "low" | "medium" | "high";
  recommended_agent_count: number;
  recommended_groups?: string[];
  reasoning?: string;
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
  role_group?: string;
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
  status?: "queued" | "summarizing" | "running" | "completed" | "partial" | "failed" | "cancelled" | "orchestrating" | "researching" | "fact_checking" | "leading";
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
  summarization_provider?: string;
  summarization_config?: Record<string, any>;
  context_summary?: string;
  enable_fact_check?: boolean;
  fact_check_provider?: string;
  fact_check_config?: Record<string, any>;
  fact_check_results?: ClaimItem[] | any[];
  report_format?: string;
  report_matrix?: MatrixReport;
  auto_scale_agents?: boolean;
  min_agents?: number;
  max_agents?: number;
  complexity?: ComplexityAssessment;
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
