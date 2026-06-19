import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import RouteLoadingTransition, { type RouteLoadingVariant } from './RouteLoadingTransition';
import RouteTransitionContext, {
  ROUTE_TRANSITION_ID_STATE_KEY,
  type RouteTransitionContextValue,
  type RouteTransitionControls,
  type TransitionToOptions,
} from './RouteTransitionContext';
import { ROUTES } from '@/config/routes';

interface RouteTransitionState {
  id: string;
  variant: RouteLoadingVariant;
  progress: number;
  phase: 'working' | 'awaiting-route' | 'completing';
  exiting: boolean;
  readyFallbackMs: number;
  disableReadyFallback: boolean;
  errorMessage: string | null;
}

interface RouteTransitionProviderProps {
  children: ReactNode;
}

const PRE_READY_PROGRESS: Record<RouteLoadingVariant, number> = {
  story: 93,
  character: 91,
};

const clampProgress = (progress: number) => Math.max(0, Math.min(100, progress));
const wait = (durationMs: number) => new Promise((resolve) => window.setTimeout(resolve, durationMs));

const createTransitionId = () => (
  `route-transition-${Date.now()}-${Math.random().toString(16).slice(2)}`
);

function RouteTransitionProvider({ children }: RouteTransitionProviderProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const [transition, setTransition] = useState<RouteTransitionState | null>(null);
  const transitionRef = useRef<RouteTransitionState | null>(null);
  const frameRef = useRef<number | null>(null);
  const hideTimerRef = useRef<number | null>(null);

  useEffect(() => {
    transitionRef.current = transition;
  }, [transition]);

  const cancelFrame = useCallback(() => {
    if (frameRef.current !== null) {
      window.cancelAnimationFrame(frameRef.current);
      frameRef.current = null;
    }
  }, []);

  const setTransitionProgress = useCallback((transitionId: string, progress: number) => {
    setTransition((current) => {
      if (!current || current.id !== transitionId) return current;
      return { ...current, progress: Math.max(current.progress, clampProgress(progress)) };
    });
  }, []);

  const hideTransition = useCallback(
    (transitionId?: string) => {
      cancelFrame();
      setTransition((current) => {
        if (!current || (transitionId && current.id !== transitionId)) return current;
        return { ...current, exiting: true };
      });

      if (hideTimerRef.current !== null) window.clearTimeout(hideTimerRef.current);
      hideTimerRef.current = window.setTimeout(() => {
        setTransition((current) => {
          if (!current || (transitionId && current.id !== transitionId)) return current;
          return null;
        });
      }, 360);
    },
    [cancelFrame]
  );

  const animateTransitionTo = useCallback(
    (transitionId: string, targetProgress: number, durationMs = 700) => new Promise<void>((resolve) => {
      cancelFrame();
      const startProgress = transitionRef.current?.id === transitionId ? transitionRef.current.progress : 0;
      const target = clampProgress(targetProgress);
      const startedAt = window.performance.now();

      const step = (now: number) => {
        const elapsed = Math.min(1, (now - startedAt) / Math.max(1, durationMs));
        const eased = 1 - Math.pow(1 - elapsed, 3);
        const nextProgress = startProgress + (target - startProgress) * eased;
        setTransitionProgress(transitionId, nextProgress);

        if (elapsed < 1 && transitionRef.current?.id === transitionId) {
          frameRef.current = window.requestAnimationFrame(step);
          return;
        }

        setTransitionProgress(transitionId, target);
        frameRef.current = null;
        resolve();
      };

      frameRef.current = window.requestAnimationFrame(step);
    }),
    [cancelFrame, setTransitionProgress]
  );

  const cancelRouteTransition = useCallback(
    (transitionId?: string) => {
      hideTransition(transitionId);
    },
    [hideTransition]
  );

  const failRouteTransition = useCallback(
    (message: string, transitionId?: string) => {
      cancelFrame();
      setTransition((current) => {
        if (!current || current.exiting) return current;
        if (transitionId && current.id !== transitionId) return current;
        return {
          ...current,
          phase: 'awaiting-route',
          progress: Math.min(current.progress, 93),
          errorMessage: message,
        };
      });
    },
    [cancelFrame]
  );

  const markRouteReady = useCallback(
    async (transitionId?: string) => {
      const current = transitionRef.current;
      if (!current || current.exiting) return;
      if (transitionId && current.id !== transitionId) return;
      if (current.phase === 'completing') return;
      if (current.errorMessage) return;

      setTransition((value) => (
        value && value.id === current.id ? { ...value, phase: 'completing' } : value
      ));
      await animateTransitionTo(current.id, 100, 520);
      await wait(420);
      hideTransition(current.id);
    },
    [animateTransitionTo, hideTransition]
  );

  const transitionTo = useCallback(
    async ({
      to,
      variant,
      replace,
      state,
      preReadyProgress,
      readyFallbackMs = 12000,
      disableReadyFallback = false,
      work,
    }: TransitionToOptions) => {
      const id = createTransitionId();
      const maxBeforeReady = preReadyProgress ?? PRE_READY_PROGRESS[variant];

      if (hideTimerRef.current !== null) {
        window.clearTimeout(hideTimerRef.current);
        hideTimerRef.current = null;
      }

      setTransition({
        id,
        variant,
        progress: 4,
        phase: 'working',
        exiting: false,
        readyFallbackMs,
        disableReadyFallback,
        errorMessage: null,
      });

      try {
        await animateTransitionTo(id, 18, 420);
        const controls: RouteTransitionControls = {
          setProgress: (progress) => setTransitionProgress(id, Math.min(progress, maxBeforeReady)),
          animateTo: (progress, durationMs) => animateTransitionTo(id, Math.min(progress, maxBeforeReady), durationMs),
        };

        const result = await work?.(controls);
        if (result === false) {
          hideTransition(id);
          return false;
        }

        await animateTransitionTo(id, maxBeforeReady, 760);
        setTransition((current) => (
          current && current.id === id ? { ...current, phase: 'awaiting-route', progress: maxBeforeReady } : current
        ));
        navigate(to, {
          replace,
          state: {
            ...(state ?? {}),
            [ROUTE_TRANSITION_ID_STATE_KEY]: id,
          },
        });

        return true;
      } catch (error) {
        hideTransition(id);
        throw error;
      }
    },
    [animateTransitionTo, hideTransition, navigate, setTransitionProgress]
  );

  useEffect(() => {
    if (!transition || transition.phase !== 'awaiting-route') return;
    if (transition.disableReadyFallback || transition.errorMessage) return;
    const state = location.state as Record<string, unknown> | null;
    const routeTransitionId = state?.[ROUTE_TRANSITION_ID_STATE_KEY];
    if (routeTransitionId !== transition.id) return;

    const timer = window.setTimeout(() => {
      void markRouteReady(transition.id);
    }, transition.readyFallbackMs);

    return () => window.clearTimeout(timer);
  }, [location.state, markRouteReady, transition]);

  useEffect(() => () => {
    cancelFrame();
    if (hideTimerRef.current !== null) window.clearTimeout(hideTimerRef.current);
  }, [cancelFrame]);

  const value = useMemo<RouteTransitionContextValue>(
    () => ({
      activeTransitionId: transition?.id ?? null,
      activeVariant: transition?.variant ?? null,
      transitionTo,
      markRouteReady,
      failRouteTransition,
      cancelRouteTransition,
    }),
    [cancelRouteTransition, failRouteTransition, markRouteReady, transition?.id, transition?.variant, transitionTo]
  );

  const handleLeaveFailedGame = useCallback(
    (to: string) => {
      cancelFrame();
      navigate(to, { replace: true });
      hideTransition();
    },
    [cancelFrame, hideTransition, navigate]
  );

  return (
    <RouteTransitionContext.Provider value={value}>
      {children}
      {transition && (
        <RouteLoadingTransition
          variant={transition.variant}
          progress={transition.progress}
          exiting={transition.exiting}
          errorMessage={transition.errorMessage}
          onBackToStory={() => handleLeaveFailedGame(ROUTES.FIRST_STEP)}
          onBackHome={() => handleLeaveFailedGame(ROUTES.HOME)}
        />
      )}
    </RouteTransitionContext.Provider>
  );
}

export default RouteTransitionProvider;
