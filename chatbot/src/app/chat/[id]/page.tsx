"use client";

import React, { use } from "react";
import { ChatDashboard } from "../../../components/chat/ChatDashboard";

interface ChatDetailPageProps {
  params: Promise<{ id: string }>;
}

export default function ChatDetailPage({ params }: ChatDetailPageProps) {
  const resolvedParams = use(params);
  return <ChatDashboard initialChatId={resolvedParams.id} />;
}
