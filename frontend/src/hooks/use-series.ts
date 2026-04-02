import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { isMockMode } from "../lib/config";
import {
  liveApproveSeriesScript,
  liveCreateSeries,
  liveGetSeriesCatalog,
  liveGetSeriesDetail,
  liveGetSeriesList,
  liveGetSeriesRun,
  liveGetSeriesScriptDetail,
  liveGetSeriesScripts,
  liveGetSeriesVideoRun,
  liveRejectSeriesScript,
  liveRegenerateSeriesScript,
  liveStartSeriesRun,
  liveStartSeriesVideoRun,
  liveUpdateSeries,
} from "../lib/series-api";
import {
  mockApproveSeriesScript,
  mockCreateSeries,
  mockGetSeriesCatalog,
  mockGetSeriesDetail,
  mockGetSeriesList,
  mockGetSeriesRun,
  mockGetSeriesScriptDetail,
  mockGetSeriesScripts,
  mockGetSeriesVideoRun,
  mockRejectSeriesScript,
  mockRegenerateSeriesScript,
  mockStartSeriesRun,
  mockStartSeriesVideoRun,
  mockUpdateSeries,
} from "../lib/series-mock";
import type { SeriesInput, SeriesRun, SeriesScriptDetail, SeriesVideoRun } from "../types/domain";

const getSeriesCatalog = () => (isMockMode() ? mockGetSeriesCatalog() : liveGetSeriesCatalog());
const getSeriesList = () => (isMockMode() ? mockGetSeriesList() : liveGetSeriesList());
const getSeriesDetail = (seriesId: string) =>
  isMockMode() ? mockGetSeriesDetail(seriesId) : liveGetSeriesDetail(seriesId);
const createSeries = (input: SeriesInput) => (isMockMode() ? mockCreateSeries(input) : liveCreateSeries(input));
const updateSeries = (seriesId: string, input: SeriesInput) =>
  isMockMode() ? mockUpdateSeries(seriesId, input) : liveUpdateSeries(seriesId, input);
const getSeriesScripts = (seriesId: string) =>
  isMockMode() ? mockGetSeriesScripts(seriesId) : liveGetSeriesScripts(seriesId);
const getSeriesScriptDetail = (seriesId: string, scriptId: string) =>
  isMockMode() ? mockGetSeriesScriptDetail(seriesId, scriptId) : liveGetSeriesScriptDetail(seriesId, scriptId);
const approveSeriesScript = (seriesId: string, scriptId: string) =>
  isMockMode() ? mockApproveSeriesScript(seriesId, scriptId) : liveApproveSeriesScript(seriesId, scriptId);
const rejectSeriesScript = (seriesId: string, scriptId: string) =>
  isMockMode() ? mockRejectSeriesScript(seriesId, scriptId) : liveRejectSeriesScript(seriesId, scriptId);
const regenerateSeriesScript = (seriesId: string, scriptId: string, idempotencyKey: string) =>
  isMockMode()
    ? mockRegenerateSeriesScript(seriesId, scriptId, idempotencyKey)
    : liveRegenerateSeriesScript(seriesId, scriptId, idempotencyKey);
const startSeriesRun = (seriesId: string, requestedScriptCount: number, idempotencyKey: string) =>
  isMockMode()
    ? mockStartSeriesRun(seriesId, requestedScriptCount, idempotencyKey)
    : liveStartSeriesRun(seriesId, requestedScriptCount, idempotencyKey);
const getSeriesRun = (seriesId: string, runId: string) =>
  isMockMode() ? mockGetSeriesRun(seriesId, runId) : liveGetSeriesRun(seriesId, runId);
const startSeriesVideoRun = (seriesId: string, seriesScriptIds: string[], idempotencyKey: string) =>
  isMockMode()
    ? mockStartSeriesVideoRun(seriesId, seriesScriptIds, idempotencyKey)
    : liveStartSeriesVideoRun(seriesId, seriesScriptIds, idempotencyKey);
const getSeriesVideoRun = (seriesId: string, runId: string) =>
  isMockMode() ? mockGetSeriesVideoRun(seriesId, runId) : liveGetSeriesVideoRun(seriesId, runId);

function isActiveStatus(status?: string | null): boolean {
  return status === "queued" || status === "running" || status === "review";
}

function invalidateSeriesQueries(queryClient: ReturnType<typeof useQueryClient>, seriesId: string) {
  queryClient.invalidateQueries({ queryKey: ["series-list"] });
  queryClient.invalidateQueries({ queryKey: ["series-detail", seriesId] });
  queryClient.invalidateQueries({ queryKey: ["series-scripts", seriesId] });
  queryClient.invalidateQueries({ queryKey: ["series-script-detail", seriesId] });
}

export function useSeriesCatalog() {
  return useQuery({
    queryKey: ["series-catalog"],
    queryFn: getSeriesCatalog,
    staleTime: Infinity,
  });
}

export function useSeriesList() {
  return useQuery({
    queryKey: ["series-list"],
    queryFn: getSeriesList,
    refetchInterval: 4000,
  });
}

export function useSeriesDetail(seriesId: string) {
  return useQuery({
    queryKey: ["series-detail", seriesId],
    queryFn: () => getSeriesDetail(seriesId),
    enabled: Boolean(seriesId),
    refetchInterval: (query) => {
      const data = query.state.data as
        | { activeRunStatus?: string | null; activeVideoRunStatus?: string | null }
        | undefined;
      return isActiveStatus(data?.activeRunStatus) || isActiveStatus(data?.activeVideoRunStatus) ? 1500 : false;
    },
  });
}

export function useSeriesScripts(seriesId: string) {
  return useQuery({
    queryKey: ["series-scripts", seriesId],
    queryFn: () => getSeriesScripts(seriesId),
    enabled: Boolean(seriesId),
    refetchInterval: 1500,
  });
}

export function useSeriesScriptDetail(seriesId: string, scriptId: string, enabled = true) {
  return useQuery({
    queryKey: ["series-script-detail", seriesId, scriptId],
    queryFn: () => getSeriesScriptDetail(seriesId, scriptId),
    enabled: Boolean(seriesId && scriptId && enabled),
    refetchInterval: (query) => {
      const data = query.state.data as SeriesScriptDetail | undefined;
      return isActiveStatus(data?.script.videoStatus) || isActiveStatus(data?.latestRenderStatus) ? 1200 : false;
    },
  });
}

export function useSeriesRun(seriesId: string, runId: string | null) {
  return useQuery({
    queryKey: ["series-run", seriesId, runId],
    queryFn: () => getSeriesRun(seriesId, runId ?? ""),
    enabled: Boolean(seriesId && runId),
    refetchInterval: (query) => {
      const data = query.state.data as SeriesRun | undefined;
      return isActiveStatus(data?.status) ? 1200 : false;
    },
  });
}

export function useSeriesVideoRun(seriesId: string, runId: string | null) {
  return useQuery({
    queryKey: ["series-video-run", seriesId, runId],
    queryFn: () => getSeriesVideoRun(seriesId, runId ?? ""),
    enabled: Boolean(seriesId && runId),
    refetchInterval: (query) => {
      const data = query.state.data as SeriesVideoRun | undefined;
      return isActiveStatus(data?.status) ? 1200 : false;
    },
  });
}

export function useCreateSeries() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: SeriesInput) => createSeries(input),
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: ["series-list"] });
      queryClient.invalidateQueries({ queryKey: ["shell-data"] });
      queryClient.setQueryData(["series-detail", created.id], created);
    },
  });
}

export function useUpdateSeries(seriesId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: SeriesInput) => updateSeries(seriesId, input),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ["series-list"] });
      queryClient.setQueryData(["series-detail", seriesId], updated);
    },
  });
}

export function useApproveSeriesScript(seriesId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (scriptId: string) => approveSeriesScript(seriesId, scriptId),
    onSuccess: (_script, scriptId) => {
      invalidateSeriesQueries(queryClient, seriesId);
      queryClient.invalidateQueries({ queryKey: ["series-script-detail", seriesId, scriptId] });
    },
  });
}

export function useRejectSeriesScript(seriesId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (scriptId: string) => rejectSeriesScript(seriesId, scriptId),
    onSuccess: (_script, scriptId) => {
      invalidateSeriesQueries(queryClient, seriesId);
      queryClient.invalidateQueries({ queryKey: ["series-script-detail", seriesId, scriptId] });
    },
  });
}

export function useRegenerateSeriesScript(seriesId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ scriptId, idempotencyKey }: { scriptId: string; idempotencyKey: string }) =>
      regenerateSeriesScript(seriesId, scriptId, idempotencyKey),
    onSuccess: (run, { scriptId }) => {
      invalidateSeriesQueries(queryClient, seriesId);
      queryClient.setQueryData(["series-run", seriesId, run.id], run);
      queryClient.invalidateQueries({ queryKey: ["series-script-detail", seriesId, scriptId] });
    },
  });
}

export function useStartSeriesRun(seriesId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      requestedScriptCount,
      idempotencyKey,
    }: {
      requestedScriptCount: number;
      idempotencyKey: string;
    }) => startSeriesRun(seriesId, requestedScriptCount, idempotencyKey),
    onSuccess: (run) => {
      invalidateSeriesQueries(queryClient, seriesId);
      queryClient.setQueryData(["series-run", seriesId, run.id], run);
    },
  });
}

export function useStartSeriesVideoRun(seriesId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      seriesScriptIds,
      idempotencyKey,
    }: {
      seriesScriptIds: string[];
      idempotencyKey: string;
    }) => startSeriesVideoRun(seriesId, seriesScriptIds, idempotencyKey),
    onSuccess: (run) => {
      invalidateSeriesQueries(queryClient, seriesId);
      queryClient.setQueryData(["series-video-run", seriesId, run.id], run);
    },
  });
}
