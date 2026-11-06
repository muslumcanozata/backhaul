import { FormEvent, useEffect, useMemo, useState } from "react";
import { EyeIcon, EyeSlashIcon } from "@phosphor-icons/react";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import InputAdornment from "@mui/material/InputAdornment";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { api } from "./api";
import { BrandLogo } from "./brand";
import { pagesFor } from "./labels";
import { Ayarlar } from "./pages/Ayarlar";
import { Araclar } from "./pages/Araclar";
import { Kullanicilar } from "./pages/Kullanicilar";
import { Masa } from "./pages/Masa";
import { QueuePage } from "./pages/QueuePage";
import { Sicil } from "./pages/Sicil";
import { Soforler } from "./pages/Soforler";
import { Raporlar } from "./pages/Raporlar";
import { Takograf } from "./pages/Takograf";
import { Takip } from "./pages/Takip";
import { SessionProvider, useSession } from "./session";
import { AuthLayout, Dashboard } from "./shell";
import type { Page, User } from "./types";

export function App() {
  const [token, setToken] = useState<string | null>(() => sessionStorage.getItem("token"));
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState("");
  const session = useMemo(() => (token && user ? { token, user, notice: setError } : null), [token, user]);

  useEffect(() => {
    if (!token) return;
    api<User>("/auth/me", token)
      .then(setUser)
      .catch(() => {
        sessionStorage.removeItem("token");
        setToken(null);
        setUser(null);
      });
  }, [token]);

  function logout() {
    sessionStorage.removeItem("token");
    setToken(null);
    setUser(null);
    setError("");
    window.location.hash = "";
  }

  if (token && !user) {
    return (
      <AuthLayout>
        <Stack spacing={2} sx={{ alignItems: "center", textAlign: "center" }}>
          <BrandLogo size={48} stacked />
          <Typography color="text.secondary">Oturum açılıyor…</Typography>
        </Stack>
      </AuthLayout>
    );
  }

  if (!session) {
    return <Login onToken={setToken} error={error} onError={setError} />;
  }

  return (
    <SessionProvider value={session}>
      <Shell error={error} onLogout={logout} />
    </SessionProvider>
  );
}

function Login({
  onToken,
  error,
  onError,
}: {
  onToken: (token: string) => void;
  error: string;
  onError: (message: string) => void;
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    onError("");
    setBusy(true);
    try {
      const result = await api<{ access_token: string }>("/auth/login", null, {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      sessionStorage.setItem("token", result.access_token);
      onToken(result.access_token);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Giriş yapılamadı");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout>
      <Stack component="form" spacing={3} onSubmit={submit}>
        <Stack spacing={1.5} sx={{ alignItems: { xs: "center", sm: "flex-start" }, textAlign: { xs: "center", sm: "left" } }}>
          <BrandLogo size={56} stacked />
          <Stack spacing={0.75}>
            <Typography variant="h4">Giriş yapın</Typography>
            <Typography color="text.secondary" variant="body2">
              Firma hesabınızla sefer masasına girin.
            </Typography>
          </Stack>
        </Stack>
        <TextField
          name="email"
          label="E-posta"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          autoComplete="username"
          slotProps={{ inputLabel: { shrink: true } }}
          required
        />
        <TextField
          name="password"
          label="Parola"
          type={showPassword ? "text" : "password"}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete="current-password"
          slotProps={{
            inputLabel: { shrink: true },
            input: {
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton onClick={() => setShowPassword((value) => !value)} edge="end" aria-label={showPassword ? "Parolayı gizle" : "Parolayı göster"}>
                    {showPassword ? <EyeSlashIcon size={20} /> : <EyeIcon size={20} />}
                  </IconButton>
                </InputAdornment>
              ),
            },
          }}
          required
        />
        {error ? <Alert severity="error">{error}</Alert> : null}
        <Button type="submit" variant="contained" color="inherit" size="large" fullWidth loading={busy} disabled={busy}>
          Giriş yap
        </Button>
      </Stack>
    </AuthLayout>
  );
}

function Shell({ error, onLogout }: { error: string; onLogout: () => void }) {
  const { user } = useSession();
  const pages = useMemo(() => pagesFor(user.role), [user.role]);
  const [page, setPage] = useState<Page>(pages[0]);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    const allowed = pagesFor(user.role);

    function show(next: Page, nextFilter: string) {
      setPage(next);
      setFilter(nextFilter);
      const target = nextFilter ? `#${next}/${encodeURIComponent(nextFilter)}` : `#${next}`;
      if (window.location.hash !== target) history.replaceState(null, "", target);
    }

    function fromHash() {
      const [name, ...rest] = window.location.hash.replace("#", "").split("/");
      const current = name as Page;
      const nextFilter = rest.length ? decodeURIComponent(rest.join("/")) : "";
      show(allowed.includes(current) ? current : allowed[0], allowed.includes(current) ? nextFilter : "");
    }

    fromHash();
    window.addEventListener("hashchange", fromHash);
    return () => window.removeEventListener("hashchange", fromHash);
  }, [user.role]);

  function open(next: Page) {
    window.location.hash = next;
    setPage(next);
    setFilter("");
  }

  return (
    <Dashboard user={user} pages={pages} page={page} onOpen={open} onLogout={onLogout}>
      <Stack spacing={2}>
        {error ? <Alert severity="error">{error}</Alert> : null}
        {page === "firmalar" ? <Sicil /> : null}
        {page === "masa" ? <Masa /> : null}
        {page === "gidis" ? <QueuePage direction="gidis" /> : null}
        {page === "donus" ? <QueuePage direction="donus" /> : null}
        {page === "takip" ? <Takip initialVehicle={filter} /> : null}
        {page === "araclar" ? <Araclar initialFilter={filter} /> : null}
        {page === "soforler" ? <Soforler /> : null}
        {page === "takograf" ? <Takograf initialDriver={filter} /> : null}
        {page === "raporlar" ? <Raporlar initialReport={filter} /> : null}
        {page === "ayarlar" ? <Ayarlar /> : null}
        {page === "kullanicilar" ? <Kullanicilar /> : null}
      </Stack>
    </Dashboard>
  );
}
