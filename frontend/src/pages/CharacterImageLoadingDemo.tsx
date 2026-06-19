import { useEffect, useState } from 'react';
import RouteLoadingTransition from '@/components/RouteLoadingTransition';

const progressMarks = [12, 31, 56, 78, 91];

function CharacterImageLoadingDemo() {
  const [activeStage, setActiveStage] = useState(0);

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      setActiveStage((current) => Math.min(current + 1, progressMarks.length - 1));
    }, 2400);

    return () => window.clearInterval(intervalId);
  }, []);

  const progress = progressMarks[activeStage];

  return <RouteLoadingTransition variant="character" progress={progress} />;
}

export default CharacterImageLoadingDemo;
