"use client";

import { useState, useRef, useCallback } from "react";
import { transcribeVoiceAudio } from "./api";

interface UseVoiceRecordingOptions {
  onTranscribed?: (text: string) => void;
  onError?: (error: string) => void;
}

export function useVoiceRecording(options: UseVoiceRecordingOptions = {}) {
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [isTranscribing, setIsTranscribing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  const startRecording = useCallback(async () => {
    setError(null);
    if (typeof window === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      const err = "Trình duyệt không hỗ trợ API thu âm (MediaDevices).";
      setError(err);
      options.onError?.(err);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      // Determine supported mime type
      let mimeType = "audio/webm";
      if (typeof MediaRecorder !== "undefined") {
        if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
          mimeType = "audio/webm;codecs=opus";
        } else if (MediaRecorder.isTypeSupported("audio/ogg;codecs=opus")) {
          mimeType = "audio/ogg;codecs=opus";
        } else if (MediaRecorder.isTypeSupported("audio/mp4")) {
          mimeType = "audio/mp4";
        }
      }

      const recorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.start(250); // collect chunks every 250ms
      setIsRecording(true);
    } catch (err: any) {
      const errMsg = err?.name === "NotAllowedError"
        ? "Quyền truy cập micro đã bị từ chối. Vui lòng cấp quyền micro trong cài đặt trình duyệt."
        : `Không thể khởi động micro: ${err?.message || String(err)}`;
      setError(errMsg);
      options.onError?.(errMsg);
      setIsRecording(false);
    }
  }, [options]);

  const stopRecording = useCallback(async (): Promise<string> => {
    return new Promise((resolve) => {
      const recorder = mediaRecorderRef.current;
      if (!recorder || recorder.state === "inactive") {
        setIsRecording(false);
        resolve("");
        return;
      }

      recorder.onstop = async () => {
        setIsRecording(false);
        setIsTranscribing(true);

        // Stop all audio tracks to release microphone hardware
        if (streamRef.current) {
          streamRef.current.getTracks().forEach((track) => track.stop());
          streamRef.current = null;
        }

        try {
          const blobType = recorder.mimeType || "audio/webm";
          const audioBlob = new Blob(audioChunksRef.current, { type: blobType });
          const filename = blobType.includes("mp4") ? "recording.mp4" : "recording.webm";

          const result = await transcribeVoiceAudio(audioBlob, filename);
          setIsTranscribing(false);

          if (result.success && result.text) {
            options.onTranscribed?.(result.text);
            resolve(result.text);
          } else {
            const err = result.error || "Không thể chuyển đổi âm thanh thành văn bản.";
            setError(err);
            options.onError?.(err);
            resolve("");
          }
        } catch (err: any) {
          setIsTranscribing(false);
          const errStr = err?.message || String(err);
          setError(errStr);
          options.onError?.(errStr);
          resolve("");
        }
      };

      try {
        recorder.stop();
      } catch {
        setIsRecording(false);
        resolve("");
      }
    });
  }, [options]);

  const toggleRecording = useCallback(async () => {
    if (isRecording) {
      return await stopRecording();
    } else {
      await startRecording();
      return "";
    }
  }, [isRecording, startRecording, stopRecording]);

  return {
    isRecording,
    isTranscribing,
    error,
    startRecording,
    stopRecording,
    toggleRecording,
  };
}
