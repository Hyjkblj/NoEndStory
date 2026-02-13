/**
 * 加载动画组件接口
 * 所有加载动画组件都应该实现这个接口
 */
export interface LoadingAnimationProps {
  message?: string;
  className?: string;
}

export type LoadingAnimationComponent = React.ComponentType<LoadingAnimationProps>;

/**
 * 加载动画类型
 */
export type LoadingAnimationType = 
  | 'sakura'        // 樱花动画（默认）
  | 'simple'        // 简单动画
  | 'circle'        // 圆形动画
  | 'pulse'         // 脉冲动画
  | 'custom';       // 自定义动画

export const LoadingAnimationType = {
  SAKURA: 'sakura' as const,
  SIMPLE: 'simple' as const,
  CIRCLE: 'circle' as const,
  PULSE: 'pulse' as const,
  CUSTOM: 'custom' as const,
} as const;

/**
 * 加载动画配置
 */
export interface LoadingAnimationConfig {
  type: LoadingAnimationType;
  component?: LoadingAnimationComponent;  // 自定义组件
  message?: string;
  className?: string;
}
