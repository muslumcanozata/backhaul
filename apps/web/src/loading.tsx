import { CSpinner } from "@coreui/react";

export function LoadingNote({ label = "Yükleniyor…" }: { label?: string }) {
  return (
    <div className="d-flex align-items-center gap-2 px-3 py-3 text-body-secondary">
      <CSpinner size="sm" />
      <span>{label}</span>
    </div>
  );
}
