import { HelpError } from './errors';

export function requireUser(locals: App.Locals): void {
  if (!locals.user) {
    throw new HelpError(401, 'Authentication required');
  }
}

export function requireAdmin(locals: App.Locals): void {
  requireUser(locals);
  if (!locals.user?.permissions?.is_admin) {
    throw new HelpError(403, 'Admin access required.');
  }
}
