import { createContext, useContext } from "react";
import type { User } from "./types";

export type Session = {
  token: string;
  user: User;
  notice: (message: string) => void;
};

const SessionContext = createContext<Session | null>(null);

export const SessionProvider = SessionContext.Provider;

export function useSession(): Session {
  const session = useContext(SessionContext);
  if (!session) throw new Error("Oturum yok");
  return session;
}
