import { FormEvent, useEffect, useState } from "react";
import { CButton, CCard, CCardBody, CCardHeader, CFormInput, CFormLabel } from "@coreui/react";
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
    <div className="row g-3">
      <div className="col-12 col-lg-4 d-flex flex-column gap-3">
        <CCard>
          <CCardHeader>
            <strong>Firmalar</strong>
          </CCardHeader>
          <div className="list-group list-group-flush">
            {tenants.map((tenant) => (
              <button
                key={tenant.id}
                type="button"
                className={`list-group-item list-group-item-action text-start ${tenant.id === selected ? "active" : ""}`}
                onClick={() => setSelected(tenant.id)}
              >
                <div className="fw-semibold">{tenant.name}</div>
                <div className={`small ${tenant.id === selected ? "text-white-50" : "text-body-secondary"}`}>{tenant.code}</div>
              </button>
            ))}
          </div>
        </CCard>
        <CCard>
          <CCardHeader>
            <strong>Firma aç</strong>
          </CCardHeader>
          <CCardBody>
            <form className="d-flex flex-column gap-3" onSubmit={createTenant}>
              <div>
                <CFormLabel>Ad</CFormLabel>
                <CFormInput value={name} onChange={(event) => setName(event.target.value)} required />
              </div>
              <div>
                <CFormLabel>Kod</CFormLabel>
                <CFormInput value={code} onChange={(event) => setCode(event.target.value)} pattern="[a-z0-9-]+" required />
              </div>
              <CButton type="submit" color="primary">
                Kaydet
              </CButton>
            </form>
          </CCardBody>
        </CCard>
      </div>
      <div className="col-12 col-lg-8">
        <CCard>
          <CCardHeader>
            <strong>{firm?.name ?? "Firma"}</strong>
            <div className="small text-body-secondary">{firm ? `Kod ${firm.code}. Operasyon bu kabukta açılmaz.` : "Firma seçin."}</div>
          </CCardHeader>
          <CCardBody>
            {firm ? (
              <UsersPanel
                users={users}
                roles={roles}
                createPath={`/tenants/${firm.id}/users`}
                patchPath={(userId) => `/tenants/${firm.id}/users/${userId}`}
                onChanged={async () => setUsers(await api<User[]>(`/tenants/${firm.id}/users`, token))}
              />
            ) : null}
          </CCardBody>
        </CCard>
      </div>
    </div>
  );
}
