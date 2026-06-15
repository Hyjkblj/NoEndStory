import AppRouter from './router';
import { App as AntdApp } from 'antd';
import { AuthProvider } from '@/stores/authStore';
import './App.css';

function App() {
  return (
    <AntdApp>
      <AuthProvider>
        <AppRouter />
      </AuthProvider>
    </AntdApp>
  );
}

export default App;
