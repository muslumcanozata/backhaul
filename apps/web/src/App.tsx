import { FormEvent, useEffect, useMemo, useState } from "react";
import { CAlert, CButton, CForm, CFormInput, CFormLabel, CInputGroup, CInputGroupText } from "@coreui/react";
import CIcon from "@coreui/icons-react";
import { cilLockLocked, cilUser } from "@coreui/icons";
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
      .catch((err: unknown) => {
        sessionStorage.removeItem("token");
        setToken(null);
        setUser(null);
        setError(err instanceof Error ? err.message : "Oturum doğrulanamadı");
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
        <div className="text-center d-flex flex-column align-items-center gap-3">
          <BrandLogo size={48} stacked />
          <div className="text-body-secondary">Oturum açılıyor…</div>
        </div>
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
      <CForm className="d-flex flex-column gap-3" onSubmit={submit}>
        <div className="d-flex flex-column gap-2 align-items-sm-start align-items-center text-sm-start text-center">
          <BrandLogo size={56} stacked />
          <div>
            <h2 className="h4 mb-1">Giriş yapın</h2>
            <p className="text-body-secondary small mb-0">Firma hesabınızla sefer masasına girin.</p>
          </div>
        </div>
        <div>
          <CFormLabel htmlFor="email">E-posta</CFormLabel>
          <CInputGroup>
            <CInputGroupText>
              <CIcon icon={cilUser} />
            </CInputGroupText>
            <CFormInput
              id="email"
              name="email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="username"
              required
            />
          </CInputGroup>
        </div>
        <div>
          <CFormLabel htmlFor="password">Parola</CFormLabel>
          <CInputGroup>
            <CInputGroupText>
              <CIcon icon={cilLockLocked} />
            </CInputGroupText>
            <CFormInput
              id="password"
              name="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
          </CInputGroup>
        </div>
        {error ? <CAlert color="danger" className="mb-0">{error}</CAlert> : null}
        <CButton type="submit" color="primary" size="lg" disabled={busy}>
          {busy ? "Giriş yapılıyor…" : "Giriş yap"}
        </CButton>
      </CForm>
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
      <div className="d-flex flex-column gap-3 pb-4">
        {error ? <CAlert color="danger">{error}</CAlert> : null}
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
      </div>
    </Dashboard>
  );
}
