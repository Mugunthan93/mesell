// features/auth/auth.routes.ts
import { Routes } from '@angular/router';
import { AuthApiService } from './auth-api.service';

export const AUTH_ROUTES: Routes = [
  {
    path: 'signup',
    providers: [AuthApiService],
    loadComponent: () =>
      import('./signup/signup.component').then(m => m.SignupComponent),
  },
  {
    path: 'login',
    providers: [AuthApiService],
    loadComponent: () =>
      import('./login/login.component').then(m => m.LoginComponent),
  },
];
