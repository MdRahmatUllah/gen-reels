import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { VisualPreset, VoicePreset } from "../types/domain";
import {
  mockGetVisualPresets,
  mockGetVoicePresets,
  mockCreateVisualPreset,
  mockCreateVoicePreset,
} from "../lib/mock-service";

export function useVisualPresets() {
  return useQuery({
    queryKey: ["visualPresets"],
    queryFn: mockGetVisualPresets,
  });
}

export function useVoicePresets() {
  return useQuery({
    queryKey: ["voicePresets"],
    queryFn: mockGetVoicePresets,
  });
}

export function useCreateVisualPreset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (preset: Omit<VisualPreset, "id">) => mockCreateVisualPreset(preset),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["visualPresets"] });
    },
  });
}

export function useCreateVoicePreset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (preset: Omit<VoicePreset, "id">) => mockCreateVoicePreset(preset),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["voicePresets"] });
    },
  });
}
