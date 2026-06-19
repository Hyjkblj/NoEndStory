import { useContext, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import RouteTransitionContext, { ROUTE_TRANSITION_ID_STATE_KEY } from '@/components/RouteTransitionContext';

interface RouteTransitionReadyOptions {
  delayMs?: number;
}

export function useRouteTransition() {
  const context = useContext(RouteTransitionContext);
  if (!context) {
    throw new Error('useRouteTransition must be used within RouteTransitionProvider');
  }
  return context;
}

export function useRouteTransitionReady(ready: boolean, options: RouteTransitionReadyOptions = {}) {
  const { activeTransitionId, markRouteReady } = useRouteTransition();
  const location = useLocation();
  const delayMs = options.delayMs ?? 120;

  useEffect(() => {
    if (!ready) return;
    const state = location.state as Record<string, unknown> | null;
    const routeTransitionId = state?.[ROUTE_TRANSITION_ID_STATE_KEY];
    const transitionId = typeof routeTransitionId === 'string' ? routeTransitionId : activeTransitionId;
    if (!transitionId) return;

    const timer = window.setTimeout(() => {
      void markRouteReady(transitionId);
    }, delayMs);

    return () => window.clearTimeout(timer);
  }, [activeTransitionId, delayMs, location.key, location.state, markRouteReady, ready]);
}
