import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import Layout from '@/components/Layout';
import Home from '@/pages/Home';
import FirstStep from '@/pages/FirstStep';
import CharacterSetting from '@/pages/CharacterSetting';
import CharacterSelection from '@/pages/CharacterSelection';
import FirstMeetingSelection from '@/pages/FirstMeetingSelection';
import Game from '@/pages/Game';
import NotFound from '@/pages/NotFound';

const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      {
        index: true,
        element: <Home />,
      },
      {
        path: 'firststep',
        element: <FirstStep />,
      },
      {
        path: 'charactersetting',
        element: <CharacterSetting />,
      },
      {
        path: 'characterselection',
        element: <CharacterSelection />,
      },
      {
        path: 'firstmeeting',
        element: <FirstMeetingSelection />,
      },
      {
        path: 'game',
        element: <Game />,
      },
      {
        path: '*',
        element: <NotFound />,
      },
    ],
  },
]);

function AppRouter() {
  return <RouterProvider router={router} />;
}

export default AppRouter;
