import AppRouter from './router';
import { App as AntdApp } from 'antd';
import { useButtonClickSound } from './hooks';
import './App.css';

function App() {
  useButtonClickSound();

  return (
    <AntdApp>
      <AppRouter />
    </AntdApp>
  );
}

export default App;
