import type { Role } from './types';

export const DASHBOARD_PATHS: Record<Role, string> = {
  learner: '/learner',
  sme: '/sme',
  admin: '/admin',
};

export function dashboardPathFor(role: Role): string {
  return DASHBOARD_PATHS[role];
}

export const ROLE_LABELS: Record<Role, string> = {
  learner: 'Learner',
  sme: 'Subject Matter Expert',
  admin: 'Administrator',
};
