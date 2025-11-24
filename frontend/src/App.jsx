import { Routes, Route, Navigate } from 'react-router-dom'
import Welcome from './pages/Welcome'
import Home from './pages/Home'
import Vocabulary from './pages/agents/Vocabulary'
import CurrentSystem from './pages/agents/CurrentSystem'
import Volatility from './pages/agents/Volatility'
import Ambiguity from './pages/agents/Ambiguity'
import Interconnectedness from './pages/agents/Interconnectedness'
import Uncertainty from './pages/agents/Uncertainty'
import IndustryResearch from './pages/agents/IndustryResearch'
import CompanyResearch from './pages/agents/CompanyResearch'
import StandardPractices from './pages/agents/StandardPractices'
import Admin from './pages/Admin'
import IdentifyStakeholders from './pages/agents/IdentifyStakeholders'
import QuestionDiscovery from './pages/agents/QuestionDiscovery'
import ProblemComplexity from './pages/agents/ProblemComplexity'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Welcome />} />
      <Route path="/home" element={<Home />} />
      <Route path="/agents/vocabulary" element={<Vocabulary />} />
      <Route path="/agents/current-system" element={<CurrentSystem />} />
      <Route path="/agents/volatility" element={<Volatility />} />
      <Route path="/agents/ambiguity" element={<Ambiguity />} />
      <Route path="/agents/interconnectedness" element={<Interconnectedness />} />
      <Route path="/agents/uncertainty" element={<Uncertainty />} />
      <Route path="/agents/industry-research" element={<IndustryResearch />} />
      <Route path="/agents/company-research" element={<CompanyResearch />} />
      <Route path="/agents/standard-practices" element={<StandardPractices />} />
      <Route path="/admin" element={<Admin />} />
      <Route path="/agents/identify-stakeholders" element={<IdentifyStakeholders />} />
      <Route path="/agents/question-discovery" element={<QuestionDiscovery />} />
      <Route path="/agents/problem-complexity" element={<ProblemComplexity />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
