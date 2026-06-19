import { useEffect, useState } from 'react';
import RouteLoadingTransition from '@/components/RouteLoadingTransition';

const progressMarks = [18, 42, 68, 93];

function LoadingDemo() {
  const [activeStage, setActiveStage] = useState(0);

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      setActiveStage((current) => Math.min(current + 1, progressMarks.length - 1));
    }, 2600);

    return () => window.clearInterval(intervalId);
  }, []);

  const progress = progressMarks[activeStage];

  return <RouteLoadingTransition variant="story" progress={progress} />;
}

export default LoadingDemo;
