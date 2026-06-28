const trimTrailingSlash = (value: string) => value.replace(/\/+$/, '');

export const APP_BASE_PATH = (() => {
  const base = import.meta.env.BASE_URL || '/';
  if (!base || base === '/' || base === './') return '';

  const normalized = trimTrailingSlash(base.startsWith('/') ? base : `/${base}`);
  return normalized === '/' ? '' : normalized;
})();

export const getRouterBasename = () => APP_BASE_PATH || undefined;

export const withAppBasePath = (path: string): string => {
  if (!path) return APP_BASE_PATH || '/';
  if (/^(https?:|data:|blob:|file:|wss?:)/i.test(path)) return path;

  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  if (!APP_BASE_PATH || normalizedPath === APP_BASE_PATH || normalizedPath.startsWith(`${APP_BASE_PATH}/`)) {
    return normalizedPath;
  }

  return `${APP_BASE_PATH}${normalizedPath}`;
};
