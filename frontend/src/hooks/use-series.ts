import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { isMockMode } from "../lib/config";
import {
  liveCreateSeries,
  liveGetSeriesCatalog,
  liveGetSeriesDetail,
  liveGetSeriesList,
  liveGetSeriesRun,
  liveGetSeriesScripts,
  liveStartSeriesRun,
  liveUpdateSeries,
} from "../lib/series-api";
import {
  mockCreateSeries,
  mockGetSeriesCatalog,
  mockGetSeriesDetail,
  mockGetSeriesList,
  mockGetSeriesRun,
  mockGetSeriesScripts,
  mockStartSeriesRun,
  mockUpdateSeries,
} from "../lib/series-mock";
import type { SeriesInput, SeriesRun } from "../types/domain";

const getSeriesCatalog = () => (isMockMode() ? mockGetSeriesCatalog() : liveGetSeriesCatalog());
const getSeriesList = () => (isMockMode() ? mockGetSeriesList() : liveGetSeriesList());
const getSeriesDetail = (seriesId: string) =>
  isMockMode() ? mockGetSeriesDetail(seriesId) : liveGetSeriesDetail(seriesId);
const createSeries = (input: SeriesInput) => (isMockMode() ? mockCreateSeries(input) : liveCreateSeries(input));
const updateSeries = (seriesId: string, input: SeriesInput) =>
  isMockMode() ? mockUpdateSeries(seriesId, input) : liveUpdateSeries(seriesId, input);
const getSeriesScripts = (seriesId: string) =>
  isMockMode() ? mockGetSeriesScripts(seriesId) : liveGetSeriesScripts(seriesId);
const startSeriesRun = (seriesId: string, requestedScriptCount: number, idempotencyKey: string) =>
  isMockMode()
    ? mockStartSeriesRun(seriesId, requestedScriptCount, idempotencyKey)
    : liveStartSeriesRun(seriesId, requestedScriptCount, idempotencyKey);
const getSeriesRun = (seriesId: string, runId: string) =>
  isMockMode() ? mockGetSeriesRun(seriesId, runId) : liveGetSeriesRun(seriesId, runId);

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
    refetchInterval: 5000,
  });
}

export function useSeriesDetail(seriesId: string) {
  return useQuery({
    queryKey: ["series-detail", seriesId],
    queryFn: () => getSeriesDetail(seriesId),
    enabled: Boolean(seriesId),
    refetchInterval: (query) => {
      const data = query.state.data as { activeRunStatus?: string | null } | undefined;
      return data?.activeRunStatus === "queued" || data?.activeRunStatus === "running" ? 1500 : false;
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

export function useSeriesRun(seriesId: string, runId: string | null) {
  return useQuery({
    queryKey: ["series-run", seriesId, runId],
    queryFn: () => getSeriesRun(seriesId, runId ?? ""),
    enabled: Boolean(seriesId && runId),
    refetchInterval: (query) => {
      const data = query.state.data as SeriesRun | undefined;
      return data?.status === "queued" || data?.status === "running" ? 1200 : false;
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
      queryClient.invalidateQueries({ queryKey: ["series-list"] });
      queryClient.invalidateQueries({ queryKey: ["series-detail", seriesId] });
      queryClient.invalidateQueries({ queryKey: ["series-scripts", seriesId] });
      queryClient.setQueryData(["series-run", seriesId, run.id], run);
    },
  });
}
