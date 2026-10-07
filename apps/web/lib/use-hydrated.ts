import { useSyncExternalStore } from "react";

const subscribe = () => () => {};

/**
 * False during SSR and the hydration render, true afterwards. Gate UI that
 * reads persisted (localStorage) state on this to avoid hydration mismatches.
 */
export function useHydrated(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  );
}
