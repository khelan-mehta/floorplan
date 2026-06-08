// Minimal keyboard-shortcut registry. Tools/phases register handlers; a single window listener
// dispatches by a normalized key signature (e.g. "ctrl+z", "2", "3").

type Handler = (e: KeyboardEvent) => void;

const registry = new Map<string, Handler>();

function signature(e: KeyboardEvent): string {
  const parts: string[] = [];
  if (e.ctrlKey || e.metaKey) parts.push('ctrl');
  if (e.shiftKey) parts.push('shift');
  if (e.altKey) parts.push('alt');
  parts.push(e.key.toLowerCase());
  return parts.join('+');
}

export function registerShortcut(combo: string, handler: Handler): () => void {
  registry.set(combo, handler);
  return () => registry.delete(combo);
}

let installed = false;
export function installShortcuts(): void {
  if (installed || typeof window === 'undefined') return;
  installed = true;
  window.addEventListener('keydown', (e) => {
    const handler = registry.get(signature(e));
    if (handler) handler(e);
  });
}
