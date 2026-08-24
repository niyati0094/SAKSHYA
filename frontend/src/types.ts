export type Role = 'learner' | 'sme' | 'admin';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  designation: string | null;
  organization: string | null;
  is_prototype_data: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in_minutes: number;
  user: User;
}

export interface DashboardPayload {
  user: User;
  capabilities: string[];
  pending_modules: string[];
  prototype_notice: string;
}

export interface HealthPayload {
  status: string;
  app: string;
  environment: string;
  database: string;
}
