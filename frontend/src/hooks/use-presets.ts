import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { VisualPreset, VoicePreset } from "../types/domain";
import {
  mockGetVisualPresets,
  mockGetVoicePresets,
  mockCreateVisualPreset,
  mockCreateVoicePreset,
} from "../lib/mock-service";
import {
  liveGetVisualPresets,
  liveGetVoicePresets,
  liveCreateVisualPreset,
  liveCreateVoicePreset,
} from "../lib/live-api";
import { isMockMode } from "../lib/config";

export function useVisualPresets() {
  return useQuery({
    queryKey: ["visualPresets"],
    queryFn: isMockMode() ? mockGetVisualPresets : liveGetVisualPresets,
  });
}

export function useVoicePresets() {
  return useQuery({
    queryKey: ["voicePresets"],
    queryFn: isMockMode() ? mockGetVoicePresets : liveGetVoicePresets,
  });
}

export function useCreateVisualPreset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (preset: Omit<VisualPreset, "id">) =>
      isMockMode() ? mockCreateVisualPreset(preset) : liveCreateVisualPreset(preset),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["visualPresets"] });
    },
  });
}

export function useCreateVoicePreset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (preset: Omit<VoicePreset, "id">) =>
      isMockMode() ? mockCreateVoicePreset(preset) : liveCreateVoicePreset(preset),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["voicePresets"] });
    },
  });
}
