import { AnimatePresence } from 'framer-motion';
import { useBoothSSE } from './hooks/useBoothSSE';
import { useBoothStore } from './stores/boothStore';
import Welcome from './pages/Welcome';
import Presenting from './pages/Presenting';
import Thinking from './pages/Thinking';
import Reviewing from './pages/Reviewing';
import PhotoOutput from './pages/PhotoOutput';

const stepComponents: Record<string, React.ComponentType> = {
  welcome: Welcome,
  presenting: Presenting,
  thinking: Thinking,
  reviewing: Reviewing,
  photo: PhotoOutput,
  complete: PhotoOutput,
};

function App() {
  useBoothSSE();
  const step = useBoothStore((state) => state.step);
  const error = useBoothStore((state) => state.data.error);

  const PageComponent = stepComponents[step] || Welcome;

  return (
    <div className="w-screen h-screen bg-black overflow-hidden">
      <AnimatePresence mode="wait">
        {error ? (
          <div
            key="error"
            className="flex items-center justify-center w-full h-full px-8"
          >
            <p className="text-red-400 text-xl md:text-2xl text-center">
              {error}
            </p>
          </div>
        ) : (
          <PageComponent key={step} />
        )}
      </AnimatePresence>
    </div>
  );
}

export default App;
