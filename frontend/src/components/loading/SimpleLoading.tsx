import { Spin, Typography } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';
import type { LoadingAnimationProps } from './types';
import './SimpleLoading.css';

const { Text } = Typography;

function SimpleLoading({ message = '正在加载...' }: LoadingAnimationProps) {
  return (
    <div className="simple-loading-screen">
      <div className="simple-loading-backdrop" />
      <div className="simple-loading-content">
        <Spin
          indicator={<LoadingOutlined style={{ fontSize: 48, color: '#ffb3d9' }} spin />}
          size="large"
        />
        <Text className="simple-loading-text">{message}</Text>
      </div>
    </div>
  );
}

export default SimpleLoading;

