import { useEffect, useState } from "react";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CardHeader from "@mui/material/CardHeader";
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
    <Card>
      <CardHeader title="Kullanıcılar" subheader="Operasyoncu ve izleyici bu firmaya aittir. Firma yöneticisini platform sicili açar." />
      <CardContent>
        <UsersPanel users={users} roles={["dispatcher", "viewer"]} createPath="/users" patchPath={(userId) => `/users/${userId}`} onChanged={reload} />
      </CardContent>
    </Card>
  );
}
