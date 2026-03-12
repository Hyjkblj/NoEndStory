import AppRouter from './router';
import { App as AntdApp } from 'antd';
import './App.css';

function App() {
  return (
    <AntdApp>
      <AppRouter />
    </AntdApp>
  );
}

export default App;
