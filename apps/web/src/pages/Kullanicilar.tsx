import { useEffect, useState } from "react";
import { CCard, CCardBody, CCardHeader } from "@coreui/react";
import { api } from "../api";
import { useSession } from "../session";
import type { User } from "../types";
import { UsersPanel } from "./UsersPanel";

export function Kullanicilar() {
  const { token, notice } = useSession();
  const [users, setUsers] = useState<User[]>([]);

  async function reload() {
    setUsers(await api<User[]>("/users", token));
  }

  useEffect(() => {
    reload().catch((err: Error) => notice(err.message));
  }, [token]);

  return (
    <CCard>
      <CCardHeader>
        <strong>Kullanıcılar</strong>
        <div className="small text-body-secondary">Operasyoncu ve izleyici bu firmaya aittir. Firma yöneticisini platform sicili açar.</div>
      </CCardHeader>
      <CCardBody>
        <UsersPanel users={users} roles={["dispatcher", "viewer"]} createPath="/users" patchPath={(userId) => `/users/${userId}`} onChanged={reload} />
      </CCardBody>
    </CCard>
  );
}
