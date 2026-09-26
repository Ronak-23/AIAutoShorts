/**
 * ui/src/context/PipelineContext.js
 * =================================
 * Global state for channels, active pipeline runs, and notifications.
 */

import { html, createContext, useState, useEffect, useContext, useCallback, useRef } from '../html.js';
import { api } from '../api/client.js';
import { useAuth } from './AuthContext.js';

const PipelineContext = createContext(null);

export function PipelineProvider({ children }) {
  const { user } = useAuth();
  const [channels, setChannels] = useState([]);
  const [activeChannel, setActiveChannel] = useState(null);
  const [runs, setRuns] = useState([]);
  const [activeRunId, setActiveRunId] = useState(null);
  const [activeRun, setActiveRun] = useState(null);
  const [toast, setToast] = useState(null);
  const activeRunIdRef = useRef(null);

  useEffect(() => {
    activeRunIdRef.current = activeRunId;
  }, [activeRunId]);

  const showToast = (message, type = "info") => {
    setToast({ message, type, id: Date.now() });
    setTimeout(() => {
      setToast((curr) => (curr && curr.message === message ? null : curr));
    }, 4000);
  };

  const refreshChannels = useCallback(async () => {
    if (!user) return;
    try {
      const list = await api.channels.list();
      setChannels(list || []);
      if (list && list.length > 0) {
        setActiveChannel((curr) => {
          if (curr && list.find((c) => c.id === curr.id)) {
            return list.find((c) => c.id === curr.id);
          }
          return list[0];
        });
      }
    } catch (err) {
      console.error("Failed to load channels", err);
    }
  }, [user]);

  const refreshRuns = useCallback(async () => {
    if (!user) return;
    try {
      const list = await api.pipeline.listRuns();
      setRuns(list || []);
      const currentId = activeRunIdRef.current;
      if (currentId && list) {
        const found = list.find((r) => r.run_id === currentId);
        if (found) {
          setActiveRun((prev) => {
            if (!prev) return found;
            if (
              prev.status !== found.status ||
              prev.current_node !== found.current_node ||
              prev.progress_percentage !== found.progress_percentage ||
              prev.error !== found.error ||
              prev.final_video_path !== found.final_video_path ||
              prev.story_title !== found.story_title ||
              prev.qc_score !== found.qc_score ||
              (prev.completed_nodes || []).length !== (found.completed_nodes || []).length
            ) {
              return found;
            }
            return prev;
          });
        }
      } else if (list && list.length > 0) {
        setActiveRun((prev) => prev || list[0]);
        setActiveRunId((prev) => {
          if (!prev) {
            activeRunIdRef.current = list[0].run_id;
            return list[0].run_id;
          }
          return prev;
        });
      }
    } catch (err) {
      console.error("Failed to load runs", err);
    }
  }, [user]);

  useEffect(() => {
    if (user) {
      refreshChannels();
      refreshRuns();
    }
  }, [user, refreshChannels, refreshRuns]);

  // Periodic polling for active runs
  useEffect(() => {
    if (!user) return;
    const interval = setInterval(() => {
      setRuns((currentRuns) => {
        const hasRunning = (currentRuns || []).some(
          (r) => r.status === "running" || r.status === "paused_for_approval"
        );
        if (hasRunning) {
          refreshRuns();
        }
        return currentRuns;
      });
    }, 4000);
    return () => clearInterval(interval);
  }, [user, refreshRuns]);

  const selectRun = (runId) => {
    setActiveRunId(runId);
    activeRunIdRef.current = runId;
    setRuns((currentRuns) => {
      const found = (currentRuns || []).find((r) => r.run_id === runId);
      if (found) setActiveRun(found);
      return currentRuns;
    });
  };

  const startNewRun = async (requestData) => {
    try {
      const status = await api.pipeline.startRun(requestData);
      showToast(`Short generation started: ${status.run_id}`, "success");
      setActiveRunId(status.run_id);
      activeRunIdRef.current = status.run_id;
      setActiveRun(status);
      await refreshRuns();
      return status;
    } catch (err) {
      showToast(`Failed to start generation: ${err.message}`, "error");
      throw err;
    }
  };

  const cleanStaleRuns = async () => {
    try {
      await api.pipeline.cleanStaleRuns();
      showToast("Reconciled inactive production runs.", "info");
      await refreshRuns();
    } catch (err) {
      showToast(`Clean failed: ${err.message}`, "error");
    }
  };

  return html`
    <${PipelineContext.Provider} value=${{
      channels,
      activeChannel,
      setActiveChannel,
      refreshChannels,
      runs,
      activeRun,
      activeRunId,
      selectRun,
      refreshRuns,
      startNewRun,
      cleanStaleRuns,
      toast,
      showToast
    }}>
      ${children}
    <//>
  `;
}

export function usePipeline() {
  return useContext(PipelineContext);
}
