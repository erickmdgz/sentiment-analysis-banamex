import { Navigate, Route, Routes } from 'react-router-dom';
import { AuthGuard } from '@/components/AuthGuard';
import { Layout } from '@/components/Layout';
import { LoginPage } from '@/pages/LoginPage';
import { UploadPage } from '@/pages/UploadPage';
import { NationalYTDPage } from '@/pages/NationalYTDPage';
import { NationalComparePage } from '@/pages/NationalComparePage';
import { BranchesIndexPage } from '@/pages/BranchesIndexPage';
import { BranchYTDPage } from '@/pages/BranchYTDPage';
import { BranchComparePage } from '@/pages/BranchComparePage';
import { AdminPage } from '@/pages/AdminPage';

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <AuthGuard>
            <Layout />
          </AuthGuard>
        }
      >
        <Route index element={<Navigate to="/national" replace />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/national" element={<NationalYTDPage />} />
        <Route path="/national/compare" element={<NationalComparePage />} />
        <Route path="/branches" element={<BranchesIndexPage />} />
        <Route path="/branches/:branchId" element={<BranchYTDPage />} />
        <Route path="/branches/:branchId/compare" element={<BranchComparePage />} />
        <Route path="/admin/*" element={<AdminPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/national" replace />} />
    </Routes>
  );
}
