export function BrandLogo({
  size = 36,
  withWordmark = true,
  stacked = false,
}: {
  size?: number;
  withWordmark?: boolean;
  stacked?: boolean;
}) {
  return (
    <div className={`d-flex align-items-center gap-2 ${stacked ? "flex-column text-center" : ""}`}>
      <img src="/logo.png" alt="" width={size} height={size} className="rounded" style={{ display: "block", flexShrink: 0 }} />
      {withWordmark ? (
        <span className="brand-wordmark" style={{ fontSize: stacked ? "1.75rem" : "1.25rem" }}>
          Backhaul
        </span>
      ) : null}
    </div>
  );
}
