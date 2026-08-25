import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthProvider } from '../auth/AuthContext';
import { ProtectedRoute } from '../components/ProtectedRoute';
import { setToken } from '../api/client';

const LEARNER = {
  id: 1,
  email: 'learner@sakshya.dev',
  full_name: 'Ananya Rao',
  role: 'learner',
  designation: null,
  organization: null,
  is_prototype_data: true,
};

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<div>Login screen</div>} />
          <Route
            path="/learner"
            element={
              <ProtectedRoute allowedRoles={['learner']}>
                <div>Learner workspace</div>
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <div>Admin workspace</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe('route guards', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('sends an anonymous visitor to the login screen', async () => {
    renderAt('/learner');
    expect(await screen.findByText('Login screen')).toBeInTheDocument();
  });

  it('admits an authenticated learner to their own workspace', async () => {
    setToken('valid');
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => LEARNER } as Response),
    );

    renderAt('/learner');
    expect(await screen.findByText('Learner workspace')).toBeInTheDocument();
  });

  it("redirects a learner away from another role's workspace", async () => {
    // Mirrors the server's RBAC rule rather than showing a dead end.
    setToken('valid');
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => LEARNER } as Response),
    );

    renderAt('/admin');

    await waitFor(() => {
      expect(screen.queryByText('Admin workspace')).not.toBeInTheDocument();
    });
  });

  it('drops a rejected token and returns to login', async () => {
    setToken('expired');
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: false, status: 401, json: async () => ({}) } as Response),
    );

    renderAt('/learner');

    expect(await screen.findByText('Login screen')).toBeInTheDocument();
    expect(localStorage.getItem('sakshya.token')).toBeNull();
  });
});
