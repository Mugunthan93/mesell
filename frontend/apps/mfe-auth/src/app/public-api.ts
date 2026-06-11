// mfe-auth — public surface (the federation typed boundary, MASTER_PLAN §6.5).
// THREE-expose remote (D37): re-exports all three exposed components. The shell's
// loadRemoteWithFallback helper resolves each exposed symbol from one remoteEntry.json.
export { LoginComponent } from './login.component';
export { SignupComponent } from './signup.component';
export { OtpVerifyComponent } from './otp-verify.component';
