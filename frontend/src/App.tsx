import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import ExamPicker from './pages/ExamPicker';
import Exam from './pages/Exam';
import Practice from './pages/Practice';
import PracticeDone from './pages/PracticeDone';
import Report from './pages/Report';
import { ExamProvider } from './context/ExamContext';
import { UIFeedbackProvider } from './context/UIFeedbackContext';

function App() {
  return (
    <UIFeedbackProvider>
      <ExamProvider>
        <Router>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/exam" element={<ExamPicker />} />
            <Route path="/exam/:examId" element={<Exam />} />
            <Route path="/practice" element={<Practice />} />
            <Route path="/practice/done" element={<PracticeDone />} />
            <Route path="/report/:examId" element={<Report />} />
          </Routes>
        </Router>
      </ExamProvider>
    </UIFeedbackProvider>
  );
}

export default App;
