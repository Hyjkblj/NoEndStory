import { getStaticAssetUrl } from '@/services/api';

const DEFAULT_IMAGE_TIMEOUT_MS = 12000;

export const preloadImage = (url?: string | null, timeoutMs = DEFAULT_IMAGE_TIMEOUT_MS) => new Promise<boolean>((resolve) => {
  if (!url) {
    resolve(false);
    return;
  }

  const image = new Image();
  const timer = window.setTimeout(() => {
    image.onload = null;
    image.onerror = null;
    resolve(false);
  }, timeoutMs);

  image.onload = () => {
    window.clearTimeout(timer);
    resolve(true);
  };
  image.onerror = () => {
    window.clearTimeout(timer);
    resolve(false);
  };
  image.src = getStaticAssetUrl(url);
});

export const preloadImages = async (urls: Array<string | null | undefined>, timeoutMs = DEFAULT_IMAGE_TIMEOUT_MS) => {
  const uniqueUrls = [...new Set(urls.filter((url): url is string => Boolean(url)))];
  await Promise.allSettled(uniqueUrls.map((url) => preloadImage(url, timeoutMs)));
};
