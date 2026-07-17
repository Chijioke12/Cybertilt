import { mount } from 'svelte';
import App from './App.svelte';

// Global error alert function
function alertError(message: string, source?: string, lineno?: number, colno?: number, error?: any) {
  let details = `Error: ${message}`;
  if (source) details += `\nSource: ${source}`;
  if (lineno) details += `\nLine: ${lineno}`;
  if (colno) details += `\nColumn: ${colno}`;
  if (error && error.stack) details += `\nStack: ${error.stack}`;
  alert(details);
}

// Bind to window for manual or external calls if needed
(window as any).alertError = alertError;

window.addEventListener('error', (event) => {
  alertError(event.message, event.filename, event.lineno, event.colno, event.error);
});

window.addEventListener('unhandledrejection', (event) => {
  const reason = event.reason;
  const message = reason instanceof Error ? reason.message : String(reason);
  alertError(`Unhandled Promise Rejection: ${message}`, undefined, undefined, undefined, reason);
});

const app = mount(App, {
  target: document.getElementById('root')!,
});

export default app;
