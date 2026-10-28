import { FormEvent, useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CardHeader from "@mui/material/CardHeader";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { api } from "../api";
import { useSession } from "../session";
import type { Role, Tenant, User } from "../types";
import { UsersPanel } from "./UsersPanel";

export function Sicil() {
  const { token, notice } = useSession();
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [users, setUsers] = useState<User[]>([]);
  const [name, setName] = useState("");
  const [code, setCode] = useState("");

  async function loadTenants() {
    const rows = await api<Tenant[]>("/tenants", token);
    setTenants(rows);
    setSelected((current) => current || rows[0]?.id || "");
  }

  useEffect(() => {
    loadTenants().catch((err: Error) => notice(err.message));
  }, [token]);

  useEffect(() => {
    if (!selected) {
      setUsers([]);
      return;
    }
    api<User[]>(`/tenants/${selected}/users`, token)
      .then(setUsers)
      .catch((err: Error) => notice(err.message));
  }, [selected, token]);

  async function createTenant(event: FormEvent) {
    event.preventDefault();
    notice("");
    try {
      const created = await api<Tenant>("/tenants", token, { method: "POST", body: JSON.stringify({ name, code }) });
      setName("");
      setCode("");
      setSelected(created.id);
      await loadTenants();
    } catch (err) {
      notice(err instanceof Error ? err.message : "Firma açılamadı");
    }
  }

  const firm = tenants.find((tenant) => tenant.id === selected);
  const roles: Role[] = ["tenant_admin", "dispatcher", "viewer"];

  return (
    <Box sx={{ display: "grid", gap: 3, gridTemplateColumns: { xs: "1fr", lg: "360px 1fr" } }}>
      <Stack spacing={3}>
        <Card>
          <CardHeader title="Firmalar" />
          <List>
            {tenants.map((tenant) => (
              <ListItemButton key={tenant.id} selected={tenant.id === selected} onClick={() => setSelected(tenant.id)}>
                <Stack>
                  <Typography variant="subtitle2">{tenant.name}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {tenant.code}
                  </Typography>
                </Stack>
              </ListItemButton>
            ))}
          </List>
        </Card>
        <Card component="form" onSubmit={createTenant}>
          <CardHeader title="Firma aç" />
          <CardContent>
            <Stack spacing={2}>
              <TextField label="Ad" value={name} onChange={(event) => setName(event.target.value)} required />
              <TextField label="Kod" value={code} onChange={(event) => setCode(event.target.value)} slotProps={{ htmlInput: { pattern: "[a-z0-9-]+" } }} required />
              <Button type="submit" variant="contained">
                Kaydet
              </Button>
            </Stack>
          </CardContent>
        </Card>
      </Stack>
      <Card>
        <CardHeader title={firm?.name ?? "Firma"} subheader={firm ? `Kod ${firm.code}. Operasyon bu kabukta açılmaz.` : "Firma seçin."} />
        <CardContent>
          {firm ? (
            <UsersPanel
              users={users}
              roles={roles}
              createPath={`/tenants/${firm.id}/users`}
              patchPath={(userId) => `/tenants/${firm.id}/users/${userId}`}
              onChanged={async () => setUsers(await api<User[]>(`/tenants/${firm.id}/users`, token))}
            />
          ) : null}
        </CardContent>
      </Card>
    </Box>
  );
}
