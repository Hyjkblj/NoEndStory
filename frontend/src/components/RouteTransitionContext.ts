import { createContext } from 'react';
import type { RouteLoadingVariant } from './RouteLoadingTransition';

export const ROUTE_TRANSITION_ID_STATE_KEY = 'routeTransitionId';

export interface RouteTransitionControls {
  setProgress: (progress: number) => void;
  animateTo: (progress: number, durationMs?: number) => Promise<void>;
}

export interface TransitionToOptions {
  to: string;
  variant: RouteLoadingVariant;
  replace?: boolean;
  state?: Record<string, unknown>;
  preReadyProgress?: number;
  readyFallbackMs?: number;
  disableReadyFallback?: boolean;
  work?: (controls: RouteTransitionControls) => Promise<void | false> | void | false;
}

export interface RouteTransitionContextValue {
  activeTransitionId: string | null;
  activeVariant: RouteLoadingVariant | null;
  transitionTo: (options: TransitionToOptions) => Promise<boolean>;
  markRouteReady: (transitionId?: string) => Promise<void>;
  failRouteTransition: (message: string, transitionId?: string) => void;
  cancelRouteTransition: (transitionId?: string) => void;
}

const RouteTransitionContext = createContext<RouteTransitionContextValue | null>(null);

export default RouteTransitionContext;
