import { CanActivateFn } from '@angular/router';

// DESIGN-WORKTREE BYPASS: auth guard disabled for UI review on worktree-design-figma-ui-screens.
// DO NOT merge to develop — restore real guard before PR.
export const authGuard: CanActivateFn = () => true;
