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
 * 加载动画类型枚举
 */
export enum LoadingAnimationType {
  SAKURA = 'sakura',        // 樱花动画（默认）
  SIMPLE = 'simple',        // 简单动画
  CIRCLE = 'circle',        // 圆形动画
  PULSE = 'pulse',          // 脉冲动画
  CUSTOM = 'custom',        // 自定义动画
}

/**
 * 加载动画配置
 */
export interface LoadingAnimationConfig {
  type: LoadingAnimationType;
  component?: LoadingAnimationComponent;  // 自定义组件
  message?: string;
  className?: string;
}
