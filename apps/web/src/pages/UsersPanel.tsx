import { FormEvent, useState } from "react";
import { CAlert, CButton, CCard, CCardBody, CCardHeader, CFormInput, CFormLabel, CFormSelect } from "@coreui/react";
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
    <div className="d-flex flex-column gap-3">
      <div className="d-flex flex-column gap-2">
        {users.map((target) => {
          const locked = target.id === user.id || (user.role === "tenant_admin" && target.role === "tenant_admin");
          const choices = user.role === "platform_admin" ? FIRM : STAFF;
          return (
            <CCard key={target.id} className="border shadow-none">
              <CCardBody>
                <div className="d-flex flex-column flex-sm-row align-items-sm-center justify-content-between gap-2">
                  <div>
                    <div className="fw-semibold">{target.email}</div>
                    <div className="small text-body-secondary">
                      {ROLE_LABEL[target.role]} · {target.active ? "Açık" : "Kapalı"}
                    </div>
                  </div>
                  {locked ? null : (
                    <div className="d-flex flex-wrap align-items-center gap-2">
                      <div style={{ minWidth: 180 }}>
                        <CFormLabel className="visually-hidden">Rol</CFormLabel>
                        <CFormSelect
                          size="sm"
                          value={target.role}
                          onChange={(event) => patch(target, { role: event.target.value as Role })}
                        >
                          {choices.map((item) => (
                            <option key={item} value={item}>
                              {ROLE_LABEL[item]}
                            </option>
                          ))}
                        </CFormSelect>
                      </div>
                      <CButton color="secondary" variant="outline" size="sm" onClick={() => patch(target, { active: !target.active })}>
                        {target.active ? "Erişimi kapat" : "Erişimi aç"}
                      </CButton>
                    </div>
                  )}
                </div>
              </CCardBody>
            </CCard>
          );
        })}
      </div>
      <CCard>
        <CCardHeader>
          <strong>Yeni kullanıcı</strong>
        </CCardHeader>
        <CCardBody>
          <form className="d-flex flex-column gap-3" onSubmit={create}>
            <div>
              <CFormLabel>E-posta</CFormLabel>
              <CFormInput type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
            </div>
            <div>
              <CFormLabel>Parola</CFormLabel>
              <CFormInput type="password" value={password} onChange={(event) => setPassword(event.target.value)} minLength={8} required />
            </div>
            <div>
              <CFormLabel>Rol</CFormLabel>
              <CFormSelect value={role} onChange={(event) => setRole(event.target.value as Role)}>
                {roles.map((item) => (
                  <option key={item} value={item}>
                    {ROLE_LABEL[item]}
                  </option>
                ))}
              </CFormSelect>
            </div>
            <CButton type="submit" color="primary">
              Kullanıcı aç
            </CButton>
            {saved ? <CAlert color="success" className="mb-0">{saved}</CAlert> : null}
          </form>
        </CCardBody>
      </CCard>
    </div>
  );
}
