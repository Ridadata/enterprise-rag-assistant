"use client";

import { useEffect, useState } from "react";

const STORAGE_KEY = "nexus:display-name";
const DEFAULT_NAME = "demo-user";

/** Client-only preference (not a login) used to label this browser's queries in the
 * backend's query logs -- see AskRequest.user_id in api/schemas/qa.py. */
export function useDisplayName() {
  const [name, setName] = useState(DEFAULT_NAME);

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored) setName(stored);
  }, []);

  function updateName(value: string) {
    setName(value);
    window.localStorage.setItem(STORAGE_KEY, value);
  }

  return [name, updateName] as const;
}
