import { createContext, useContext, useEffect } from 'react';

export type BackgroundMusicScopeSetter = (suppressed: boolean) => void;

export const BackgroundMusicScopeContext = createContext<BackgroundMusicScopeSetter | null>(null);

export function useBackgroundMusicScope(suppressed: boolean) {
  const setScopeSuppressed = useContext(BackgroundMusicScopeContext);

  useEffect(() => {
    if (!setScopeSuppressed) return;
    setScopeSuppressed(suppressed);
    return () => setScopeSuppressed(false);
  }, [setScopeSuppressed, suppressed]);
}
