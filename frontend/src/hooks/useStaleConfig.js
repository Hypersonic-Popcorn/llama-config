import { useState } from "react";

export function useStaleConfig() {
  const [isStale, setIsStale] = useState(false);
  const markStale = () => setIsStale(true);
  const markFresh = () => setIsStale(false);
  return { isStale, markStale, markFresh };
}
