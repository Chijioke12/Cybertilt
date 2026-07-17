import { mount } from 'svelte';
import App from './App.svelte';

// DOM polyfills for KaiOS / legacy Firefox (Gecko 48)
(function () {
  const childNodes = [
    Element.prototype,
    (window as any).CharacterData?.prototype,
    (window as any).DocumentType?.prototype
  ].filter(Boolean);

  childNodes.forEach((item) => {
    if (!item.hasOwnProperty('before')) {
      Object.defineProperty(item, 'before', {
        configurable: true,
        enumerable: true,
        writable: true,
        value: function before(this: any) {
          const argArr = Array.prototype.slice.call(arguments);
          const docFrag = document.createDocumentFragment();

          argArr.forEach((argItem) => {
            const isNode = argItem instanceof Node;
            docFrag.appendChild(isNode ? argItem : document.createTextNode(String(argItem)));
          });

          if (this.parentNode) {
            this.parentNode.insertBefore(docFrag, this);
          }
        }
      });
    }

    if (!item.hasOwnProperty('after')) {
      Object.defineProperty(item, 'after', {
        configurable: true,
        enumerable: true,
        writable: true,
        value: function after(this: any) {
          const argArr = Array.prototype.slice.call(arguments);
          const docFrag = document.createDocumentFragment();

          argArr.forEach((argItem) => {
            const isNode = argItem instanceof Node;
            docFrag.appendChild(isNode ? argItem : document.createTextNode(String(argItem)));
          });

          if (this.parentNode) {
            this.parentNode.insertBefore(docFrag, this.nextSibling);
          }
        }
      });
    }

    if (!item.hasOwnProperty('replaceWith')) {
      Object.defineProperty(item, 'replaceWith', {
        configurable: true,
        enumerable: true,
        writable: true,
        value: function replaceWith(this: any) {
          const parent = this.parentNode;
          if (!parent) return;
          const argArr = Array.prototype.slice.call(arguments);
          const docFrag = document.createDocumentFragment();

          argArr.forEach((argItem) => {
            const isNode = argItem instanceof Node;
            docFrag.appendChild(isNode ? argItem : document.createTextNode(String(argItem)));
          });

          parent.replaceChild(docFrag, this);
        }
      });
    }

    if (!item.hasOwnProperty('remove')) {
      Object.defineProperty(item, 'remove', {
        configurable: true,
        enumerable: true,
        writable: true,
        value: function remove(this: any) {
          if (this.parentNode) {
            this.parentNode.removeChild(this);
          }
        }
      });
    }
  });

  const parentNodes = [
    Element.prototype,
    Document.prototype,
    DocumentFragment.prototype
  ].filter(Boolean);

  parentNodes.forEach((item) => {
    if (!item.hasOwnProperty('append')) {
      Object.defineProperty(item, 'append', {
        configurable: true,
        enumerable: true,
        writable: true,
        value: function append(this: any) {
          const argArr = Array.prototype.slice.call(arguments);
          const docFrag = document.createDocumentFragment();

          argArr.forEach((argItem) => {
            const isNode = argItem instanceof Node;
            docFrag.appendChild(isNode ? argItem : document.createTextNode(String(argItem)));
          });

          this.appendChild(docFrag);
        }
      });
    }

    if (!item.hasOwnProperty('prepend')) {
      Object.defineProperty(item, 'prepend', {
        configurable: true,
        enumerable: true,
        writable: true,
        value: function prepend(this: any) {
          const argArr = Array.prototype.slice.call(arguments);
          const docFrag = document.createDocumentFragment();

          argArr.forEach((argItem) => {
            const isNode = argItem instanceof Node;
            docFrag.appendChild(isNode ? argItem : document.createTextNode(String(argItem)));
          });

          this.insertBefore(docFrag, this.firstChild);
        }
      });
    }
  });
})();

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
