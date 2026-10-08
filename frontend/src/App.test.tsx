import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import App from './App';

describe('M2 authenticated workspace UI boundaries', () => {
  it('renders truthful unauthenticated state and working sign-in form', () => {
    const output=renderToStaticMarkup(<App />);
    expect(output).toContain('Onboarding Companion');
    expect(output).toContain('Sign in');
    expect(output).toContain('type="email"');
    expect(output).toContain('type="password"');
    expect(output).not.toContain('Complete preparation');
    expect(output).not.toContain('Activate case');
    expect(output).not.toContain('All tasks completed');
  });
  it('labels the UI as a synthetic local/CI demonstration', () => {
    const output=renderToStaticMarkup(<App />);
    expect(output).toContain('synthetic demo');
    expect(output).toContain('not a hosted production system');
  });
});
