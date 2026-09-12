import { Routes, Route, Navigate } from 'react-router-dom'
import { AppShell } from '@/app/AppShell'
import { ConsolePage } from '@/pages/ConsolePage'
import { TracePage } from '@/pages/TracePage'
import { SubmitKnowledgePage } from '@/pages/SubmitKnowledgePage'
import { ReviewQueuePage } from '@/pages/ReviewQueuePage'
import { ManageKnowledgePage } from '@/pages/ManageKnowledgePage'

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Navigate to="/console" replace />} />
        <Route path="/console" element={<ConsolePage />} />
        <Route path="/trace" element={<TracePage />} />
        <Route path="/submit-knowledge" element={<SubmitKnowledgePage />} />
        <Route path="/review-queue" element={<ReviewQueuePage />} />
        <Route path="/manage-knowledge" element={<ManageKnowledgePage />} />
      </Routes>
    </AppShell>
  )
}
