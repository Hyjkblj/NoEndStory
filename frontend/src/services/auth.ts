/**
 * 认证API服务
 * 封装所有认证相关的API调用
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

interface TokenResponse {
  user_id: string;
  user_type: string;
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

interface UserResponse {
  user_id: string;
  user_type: string;
  username?: string;
  email?: string;
  created_at: string;
  last_login_at?: string;
  free_plays_remaining: number;
}

interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

class AuthService {
  private static instance: AuthService;
  private accessToken: string | null = null;
  private refreshToken: string | null = null;

  private constructor() {
    // 从localStorage恢复token
    this.accessToken = localStorage.getItem('access_token');
    this.refreshToken = localStorage.getItem('refresh_token');
  }

  static getInstance(): AuthService {
    if (!AuthService.instance) {
      AuthService.instance = new AuthService();
    }
    return AuthService.instance;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${API_BASE}${endpoint}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...((options.headers as Record<string, string>) || {}),
    };

    // 如果有访问token，添加到请求头
    if (this.accessToken) {
      headers['Authorization'] = `Bearer ${this.accessToken}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      const data = await response.json();

      // 如果token过期，尝试刷新
      if (response.status === 401 && this.refreshToken) {
        const refreshed = await this.refreshAccessToken();
        if (refreshed) {
          // 重试原请求
          headers['Authorization'] = `Bearer ${this.accessToken}`;
          const retryResponse = await fetch(url, {
            ...options,
            headers,
          });
          return await retryResponse.json();
        }
      }

      return data;
    } catch (error) {
      console.error('API请求失败:', error);
      throw error;
    }
  }

  /**
   * 创建游客用户
   */
  async createGuest(deviceFingerprint?: string): Promise<TokenResponse> {
    const response = await this.request<TokenResponse>('/v1/auth/guest', {
      method: 'POST',
      body: JSON.stringify({
        device_fingerprint: deviceFingerprint,
      }),
    });

    if (response.code === 200) {
      this.setTokens(response.data.access_token, response.data.refresh_token);
    }

    return response.data;
  }

  /**
   * 用户注册
   */
  async register(
    email: string,
    username: string,
    password: string,
    guestToken?: string
  ): Promise<TokenResponse> {
    const response = await this.request<TokenResponse>('/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        email,
        username,
        password,
        guest_token: guestToken,
      }),
    });

    if (response.code === 200) {
      this.setTokens(response.data.access_token, response.data.refresh_token);
    }

    return response.data;
  }

  /**
   * 用户登录
   */
  async login(email: string, password: string): Promise<TokenResponse> {
    const response = await this.request<TokenResponse>('/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({
        email,
        password,
      }),
    });

    if (response.code === 200) {
      this.setTokens(response.data.access_token, response.data.refresh_token);
    }

    return response.data;
  }

  /**
   * 刷新token
   */
  async refreshAccessToken(): Promise<boolean> {
    if (!this.refreshToken) {
      return false;
    }

    try {
      const response = await this.request<TokenResponse>('/v1/auth/refresh', {
        method: 'POST',
        body: JSON.stringify({
          refresh_token: this.refreshToken,
        }),
      });

      if (response.code === 200) {
        this.setTokens(response.data.access_token, response.data.refresh_token);
        return true;
      } else {
        this.clearTokens();
        return false;
      }
    } catch {
      this.clearTokens();
      return false;
    }
  }

  /**
   * 获取当前用户信息
   */
  async getCurrentUser(): Promise<UserResponse | null> {
    if (!this.accessToken) {
      return null;
    }

    try {
      const response = await this.request<UserResponse>('/v1/auth/me');
      if (response.code === 200) {
        return response.data;
      }
      return null;
    } catch {
      return null;
    }
  }

  /**
   * 用户登出
   */
  async logout(): Promise<void> {
    try {
      await this.request('/v1/auth/logout', {
        method: 'POST',
        body: JSON.stringify({
          access_token: this.accessToken,
          refresh_token: this.refreshToken,
        }),
      });
    } finally {
      this.clearTokens();
    }
  }

  /**
   * 游客升级为注册用户
   */
  async upgradeGuest(
    email: string,
    username: string,
    password: string
  ): Promise<TokenResponse> {
    const response = await this.request<TokenResponse>('/v1/auth/upgrade', {
      method: 'POST',
      body: JSON.stringify({
        email,
        username,
        password,
      }),
    });

    if (response.code === 200) {
      this.setTokens(response.data.access_token, response.data.refresh_token);
    }

    return response.data;
  }

  /**
   * 修改密码
   */
  async changePassword(
    currentPassword: string,
    newPassword: string
  ): Promise<void> {
    await this.request('/v1/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    });
  }

  /**
   * 请求密码重置
   */
  async requestPasswordReset(email: string): Promise<void> {
    await this.request('/v1/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify({
        email,
      }),
    });
  }

  /**
   * 确认密码重置
   */
  async confirmPasswordReset(
    token: string,
    newPassword: string
  ): Promise<void> {
    await this.request('/v1/auth/reset-password/confirm', {
      method: 'POST',
      body: JSON.stringify({
        token,
        new_password: newPassword,
      }),
    });
  }

  /**
   * 设置token
   */
  private setTokens(accessToken: string, refreshToken: string): void {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
  }

  /**
   * 清除token
   */
  private clearTokens(): void {
    this.accessToken = null;
    this.refreshToken = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }

  /**
   * 检查是否已认证
   */
  isAuthenticated(): boolean {
    return !!this.accessToken;
  }

  /**
   * 获取访问token
   */
  getAccessToken(): string | null {
    return this.accessToken;
  }
}

export const authService = AuthService.getInstance();
export type { TokenResponse, UserResponse, ApiResponse };