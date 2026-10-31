import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { Nav } from '@/components/Nav';
import { Home } from '@/pages/Home';
import { Log } from '@/pages/Log';
import { Timeline } from '@/pages/Timeline';
import { Triggers } from '@/pages/Triggers';
import { Report } from '@/pages/Report';
import { Emergency } from '@/pages/Emergency';
import { Import } from '@/pages/Import';

export default function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/log" element={<Log />} />
          <Route path="/timeline" element={<Timeline />} />
          <Route path="/triggers" element={<Triggers />} />
          <Route path="/report" element={<Report />} />
          <Route path="/emergency" element={<Emergency />} />
          <Route path="/import" element={<Import />} />
        </Routes>
        <Nav />
      </div>
    </BrowserRouter>
  );
}
