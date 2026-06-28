import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

const backendOrigin =
  process.env.VITE_BACKEND_ORIGIN ||
  (process.env.BACKEND_PORT ? `http://localhost:${process.env.BACKEND_PORT}` : 'http://localhost:8001')

const backendProxy = {
  target: backendOrigin,
  changeOrigin: true,
  secure: false,
}

const normalizeBasePath = (value?: string) => {
  if (!value || value === '/' || value === './') return ''
  const withLeadingSlash = value.startsWith('/') ? value : `/${value}`
  return withLeadingSlash.replace(/\/+$/, '')
}

const appBasePath = normalizeBasePath(process.env.VITE_APP_BASE_PATH)
const withBaseRewrite = (prefix: string) => ({
  ...backendProxy,
  rewrite: (requestPath: string) => requestPath.replace(new RegExp(`^${prefix}`), ''),
})

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        ...backendProxy,
        ws: true,
      },
      '/static': backendProxy,
      '/health': backendProxy,
      ...(appBasePath
        ? {
            [`${appBasePath}/api`]: {
              ...withBaseRewrite(appBasePath),
              ws: true,
            },
            [`${appBasePath}/static`]: withBaseRewrite(appBasePath),
            [`${appBasePath}/health`]: withBaseRewrite(appBasePath),
          }
        : {}),
    },
  },
  base: appBasePath ? `${appBasePath}/` : './', // 默认保留相对路径，设置 VITE_APP_BASE_PATH 后支持子路径部署
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    emptyOutDir: true,
  },
})
