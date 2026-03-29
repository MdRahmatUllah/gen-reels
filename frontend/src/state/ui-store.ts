import { create } from "zustand";

type RenderFilter = "all" | "running" | "blocked" | "completed";

interface StudioUiStore {
  activeWorkspaceId: string;
  activeProjectId: string;
  selectedScenes: Record<string, string>;
  renderFilter: RenderFilter;
  setActiveWorkspaceId: (workspaceId: string) => void;
  setActiveProjectId: (projectId: string) => void;
  setSelectedScene: (projectId: string, sceneId: string) => void;
  setRenderFilter: (filter: RenderFilter) => void;
}

export const useStudioUiStore = create<StudioUiStore>((set) => ({
  activeWorkspaceId: "",
  activeProjectId: "",
  selectedScenes: {},
  renderFilter: "all",
  setActiveWorkspaceId: (activeWorkspaceId) => set({ activeWorkspaceId }),
  setActiveProjectId: (activeProjectId) => set({ activeProjectId }),
  setSelectedScene: (projectId, sceneId) =>
    set((state) => ({
      selectedScenes: {
        ...state.selectedScenes,
        [projectId]: sceneId,
      },
    })),
  setRenderFilter: (renderFilter) => set({ renderFilter }),
}));
