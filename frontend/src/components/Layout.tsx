import { Outlet } from 'react-router-dom';
import { Layout as AntLayout } from 'antd';
import BackgroundMusicProvider from './BackgroundMusicProvider';
import RouteTransitionProvider from './RouteTransitionProvider';

const { Content } = AntLayout;

function Layout() {
  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Content style={{ padding: 0, background: 'transparent' }}>
        <RouteTransitionProvider>
          <BackgroundMusicProvider>
            <div style={{
              width: '100%',
              minHeight: '100vh'
            }}>
              <Outlet />
            </div>
          </BackgroundMusicProvider>
        </RouteTransitionProvider>
      </Content>
    </AntLayout>
  );
}

export default Layout;
