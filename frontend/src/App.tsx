import Header from './components/layout/Header';
import UploadPage from './components/upload/UploadPage';
import ProcessingView from './components/processing/ProcessingView';
import Dashboard from './components/results/Dashboard';
import SettingsDialog from './components/settings/SettingsDialog';
import { useStore } from './store/useStore';
import './index.css';

export default function App() {
  const { view } = useStore();

  return (
    <>
      <Header />
      <main className="flex-1 flex flex-col overflow-hidden">
        {view === 'upload' && <UploadPage />}
        {view === 'processing' && <ProcessingView />}
        {view === 'results' && <Dashboard />}
      </main>
      <SettingsDialog />
    </>
  );
}
