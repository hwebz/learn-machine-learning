export interface OptionItem {
  id: string;
  label: string;
  description?: string;
  selected: boolean;
  badge?: string;
  metadata?: Record<string, any>;
}

export interface SupportedDataTypes {
  text: boolean;
  image: boolean;
  file: boolean;
  audio: boolean;
  video: boolean;
  max_file_size_mb?: number;
  supported_mime_types: string[];
}

export interface VoiceChatSupport {
  supported: boolean;
  mode: "backend_stt" | "browser_stt" | "none";
  details?: string;
}

export interface ProviderLiveCapabilities {
  provider: string;
  synced_at: string;
  is_live_dom: boolean;
  available_models: OptionItem[];
  selected_model_id?: string;
  thinking_levels: OptionItem[];
  selected_thinking_level_id?: string;
  modes: OptionItem[];
  selected_mode_id?: string;
  account_type?: string;
  supported_data_types: SupportedDataTypes;
  voice_chat: VoiceChatSupport;
  deep_thinking?: boolean;
  web_search?: boolean;
  last_error?: string | null;
}

export interface ProviderSelectionConfig {
  model_id?: string;
  thinking_level_id?: string;
  mode_id?: string;
  deep_thinking?: boolean;
  web_search?: boolean;
}
