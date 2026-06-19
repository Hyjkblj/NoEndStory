import { createBrowserRouter, createHashRouter, RouterProvider } from 'react-router-dom';
import { ROUTES } from '@/config/routes';
import Layout from '@/components/Layout';
import Home from '@/pages/Home';
import FirstStep from '@/pages/FirstStep';
import CharacterSetting from '@/pages/CharacterSetting';
import CharacterSelection from '@/pages/CharacterSelection';
import FirstMeetingSelection from '@/pages/FirstMeetingSelection';
import Game from '@/pages/Game';
import EndingArchive from '@/pages/EndingArchive';
import CharacterImageLoadingDemo from '@/pages/CharacterImageLoadingDemo';
import LoadingDemo from '@/pages/LoadingDemo';
import NotFound from '@/pages/NotFound';

const routes = [
  {
    path: ROUTES.HOME,
    element: <Layout />,
    children: [
      { index: true, element: <Home /> },
      { path: 'firststep', element: <FirstStep /> },
      { path: 'charactersetting', element: <CharacterSetting /> },
      { path: 'characterselection', element: <CharacterSelection /> },
      { path: 'firstmeeting', element: <FirstMeetingSelection /> },
      { path: 'game', element: <Game /> },
      { path: 'endingarchive', element: <EndingArchive /> },
      { path: 'loading-demo', element: <LoadingDemo /> },
      { path: 'character-image-demo', element: <CharacterImageLoadingDemo /> },
      { path: '*', element: <NotFound /> },
    ],
  },
];

const isFileProtocol = typeof window !== 'undefined' && window.location.protocol === 'file:';
const router = (isFileProtocol ? createHashRouter : createBrowserRouter)(routes);

function AppRouter() {
  return <RouterProvider router={router} />;
}

export default AppRouter;
