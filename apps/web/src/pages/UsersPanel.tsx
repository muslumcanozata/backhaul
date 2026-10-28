import { FormEvent, useState } from "react";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CardHeader from "@mui/material/CardHeader";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { api } from "../api";
import { ROLE_LABEL } from "../labels";
import { useSession } from "../session";
import type { Role, User } from "../types";

const STAFF: Role[] = ["dispatcher", "viewer"];
const FIRM: Role[] = ["tenant_admin", "dispatcher", "viewer"];

export function UsersPanel({
  users,
  roles,
  createPath,
  patchPath,
  onChanged,
}: {
  users: User[];
  roles: Role[];
  createPath: string;
  patchPath: (userId: string) => string;
  onChanged: () => Promise<void>;
}) {
  const { token, user, notice } = useSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>(roles[0]);
  const [saved, setSaved] = useState("");

  async function create(event: FormEvent) {
    event.preventDefault();
    notice("");
    setSaved("");
    try {
      await api(createPath, token, { method: "POST", body: JSON.stringify({ email, password, role }) });
      setEmail("");
      setPassword("");
      setSaved("Kullanıcı açıldı");
      await onChanged();
    } catch (err) {
      notice(err instanceof Error ? err.message : "Kullanıcı açılamadı");
    }
  }

  async function patch(target: User, body: { role?: Role; active?: boolean }) {
    notice("");
    setSaved("");
    try {
      await api(patchPath(target.id), token, { method: "PATCH", body: JSON.stringify(body) });
      setSaved("Erişim güncellendi");
      await onChanged();
    } catch (err) {
      notice(err instanceof Error ? err.message : "Erişim güncellenemedi");
    }
  }

  return (
    <Stack spacing={3}>
      <Stack spacing={1}>
        {users.map((target) => {
          const locked = target.id === user.id || (user.role === "tenant_admin" && target.role === "tenant_admin");
          const choices = user.role === "platform_admin" ? FIRM : STAFF;
          return (
            <Card key={target.id} variant="outlined" sx={{ boxShadow: "none" }}>
              <CardContent>
                <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ alignItems: { sm: "center" }, justifyContent: "space-between" }}>
                  <div>
                    <Typography variant="subtitle1">{target.email}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {ROLE_LABEL[target.role]} · {target.active ? "Açık" : "Kapalı"}
                    </Typography>
                  </div>
                  {locked ? null : (
                    <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                      <TextField
                        select
                        size="small"
                        label="Rol"
                        value={target.role}
                        onChange={(event) => patch(target, { role: event.target.value as Role })}
                        sx={{ minWidth: 180 }}
                      >
                        {choices.map((item) => (
                          <MenuItem key={item} value={item}>
                            {ROLE_LABEL[item]}
                          </MenuItem>
                        ))}
                      </TextField>
                      <Button variant="outlined" onClick={() => patch(target, { active: !target.active })}>
                        {target.active ? "Erişimi kapat" : "Erişimi aç"}
                      </Button>
                    </Stack>
                  )}
                </Stack>
              </CardContent>
            </Card>
          );
        })}
      </Stack>
      <Card component="form" onSubmit={create}>
        <CardHeader title="Yeni kullanıcı" />
        <CardContent>
          <Stack spacing={2}>
            <TextField label="E-posta" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
            <TextField label="Parola" type="password" value={password} onChange={(event) => setPassword(event.target.value)} slotProps={{ htmlInput: { minLength: 8 } }} required />
            <TextField select label="Rol" value={role} onChange={(event) => setRole(event.target.value as Role)}>
              {roles.map((item) => (
                <MenuItem key={item} value={item}>
                  {ROLE_LABEL[item]}
                </MenuItem>
              ))}
            </TextField>
            <Button type="submit" variant="contained">
              Kullanıcı aç
            </Button>
            {saved ? <Alert severity="success">{saved}</Alert> : null}
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
}
