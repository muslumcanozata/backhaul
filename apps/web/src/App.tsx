import { FormEvent, useEffect, useMemo, useState } from "react";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { api } from "./api";
import { pagesFor } from "./labels";
import { Ayarlar } from "./pages/Ayarlar";
import { Araclar } from "./pages/Araclar";
import { Kullanicilar } from "./pages/Kullanicilar";
import { Masa } from "./pages/Masa";
import { QueuePage } from "./pages/QueuePage";
import { Sicil } from "./pages/Sicil";
import { Soforler } from "./pages/Soforler";
import { Takip } from "./pages/Takip";
import { Uyarilar } from "./pages/Uyarilar";
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
        <Typography color="text.secondary">Oturum açılıyor</Typography>
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

  async function submit(event: FormEvent) {
    event.preventDefault();
    onError("");
    try {
      const result = await api<{ access_token: string }>("/auth/login", null, {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      sessionStorage.setItem("token", result.access_token);
      onToken(result.access_token);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Giriş yapılamadı");
    }
  }

  return (
    <AuthLayout>
      <Stack component="form" spacing={3} onSubmit={submit}>
        <Stack spacing={1}>
          <Typography variant="h4">Giriş</Typography>
          <Typography color="text.secondary" variant="body2">
            Firma hesabınızla sefer masasına girin.
          </Typography>
        </Stack>
        <TextField label="E-posta" type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="username" required />
        <TextField
          label="Parola"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete="current-password"
          required
        />
        {error ? <Alert severity="error">{error}</Alert> : null}
        <Button type="submit" variant="contained" color="inherit" size="large" fullWidth>
          Giriş
        </Button>
      </Stack>
    </AuthLayout>
  );
}

function Shell({ error, onLogout }: { error: string; onLogout: () => void }) {
  const { user } = useSession();
  const pages = useMemo(() => pagesFor(user.role), [user.role]);
  const [page, setPage] = useState<Page>(pages[0]);

  useEffect(() => {
    const allowed = pagesFor(user.role);

    function show(next: Page) {
      setPage(next);
      if (window.location.hash !== `#${next}`) history.replaceState(null, "", `#${next}`);
    }

    function fromHash() {
      const current = window.location.hash.replace("#", "") as Page;
      show(allowed.includes(current) ? current : allowed[0]);
    }

    fromHash();
    window.addEventListener("hashchange", fromHash);
    return () => window.removeEventListener("hashchange", fromHash);
  }, [user.role]);

  function open(next: Page) {
    window.location.hash = next;
    setPage(next);
  }

  return (
    <Dashboard user={user} pages={pages} page={page} onOpen={open} onLogout={onLogout}>
      <Stack spacing={2}>
        {error ? <Alert severity="error">{error}</Alert> : null}
        {page === "firmalar" ? <Sicil /> : null}
        {page === "masa" ? <Masa /> : null}
        {page === "gidis" ? <QueuePage direction="gidis" /> : null}
        {page === "donus" ? <QueuePage direction="donus" /> : null}
        {page === "takip" ? <Takip /> : null}
        {page === "uyarilar" ? <Uyarilar /> : null}
        {page === "araclar" ? <Araclar /> : null}
        {page === "soforler" ? <Soforler /> : null}
        {page === "ayarlar" ? <Ayarlar /> : null}
        {page === "kullanicilar" ? <Kullanicilar /> : null}
      </Stack>
    </Dashboard>
  );
}
