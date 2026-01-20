import { Outlet } from 'react-router-dom';
import { Layout as AntLayout } from 'antd';

const { Content } = AntLayout;

function Layout() {
  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Content style={{ padding: 0, background: 'transparent' }}>
        <div style={{ 
          width: '100%',
          minHeight: '100vh'
        }}>
          <Outlet />
        </div>
      </Content>
    </AntLayout>
  );
}

export default Layout;
