/**
 * 认证守卫组件
 * 用于保护需要认证的路由
 */

import { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Spin } from 'antd';
import { useAuth } from '@/stores/authStore';

interface AuthGuardProps {
  children: ReactNode;
  requireAuth?: boolean;
  requireGuest?: boolean;
  fallback?: ReactNode;
}

/**
 * 认证守卫组件
 * @param children 子组件
 * @param requireAuth 是否要求认证（默认true）
 * @param requireGuest 是否要求游客状态（默认false）
 * @param fallback 加载中显示的组件
 */
function AuthGuard({
  children,
  requireAuth = true,
  requireGuest = false,
  fallback,
}: AuthGuardProps) {
  const { isAuthenticated, isLoading, user } = useAuth();
  const location = useLocation();

  // 加载中状态
  if (isLoading) {
    if (fallback) {
      return <>{fallback}</>;
    }
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '100vh',
        }}
      >
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  // 要求认证但未认证
  if (requireAuth && !isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // 要求游客状态但不是游客
  if (requireGuest && user?.user_type !== 'guest') {
    return <Navigate to="/" replace />;
  }

  // 已认证但访问登录/注册页面（可选逻辑）
  if (isAuthenticated && (location.pathname === '/login' || location.pathname === '/register')) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}

/**
 * 需要认证的路由守卫
 */
export function ProtectedRoute({ children }: { children: ReactNode }) {
  return <AuthGuard requireAuth={true}>{children}</AuthGuard>;
}

/**
 * 游客专用路由守卫
 */
export function GuestRoute({ children }: { children: ReactNode }) {
  return <AuthGuard requireGuest={true}>{children}</AuthGuard>;
}

/**
 * 公开路由守卫（已认证用户重定向到首页）
 */
export function PublicRoute({ children }: { children: ReactNode }) {
  return <AuthGuard requireAuth={false}>{children}</AuthGuard>;
}

export default AuthGuard;