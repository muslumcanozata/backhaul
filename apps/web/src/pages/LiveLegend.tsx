import {
  MOTION_STATE_COLOR,
  MOTION_STATE_LABEL,
  MOTION_STATE_ORDER,
  VEHICLE_STATE_COLOR,
  VEHICLE_STATE_LABEL,
  VEHICLE_STATE_ORDER,
  type MotionState,
  type VehicleState,
} from "../labels";

export function LiveLegend({
  dutyCounts,
  motionCounts,
}: {
  dutyCounts: Map<VehicleState, number>;
  motionCounts: Map<MotionState, number>;
}) {
  return (
    <div className="d-flex flex-column gap-2 px-3 pb-3">
      <div>
        <div className="text-body-secondary small mb-1">Durum</div>
        <div className="d-flex flex-wrap gap-2">
          {VEHICLE_STATE_ORDER.map((state) => (
            <ChipRow
              key={state}
              color={VEHICLE_STATE_COLOR[state]}
              label={`${VEHICLE_STATE_LABEL[state]} ${dutyCounts.get(state) ?? 0}`}
              muted={!dutyCounts.get(state)}
            />
          ))}
        </div>
      </div>
      <div>
        <div className="text-body-secondary small mb-1">Hareket</div>
        <div className="d-flex flex-wrap gap-2">
          {MOTION_STATE_ORDER.map((state) => (
            <ChipRow
              key={state}
              color={MOTION_STATE_COLOR[state]}
              label={`${MOTION_STATE_LABEL[state]} ${motionCounts.get(state) ?? 0}`}
              muted={!motionCounts.get(state)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function ChipRow({ color, label, muted }: { color: string; label: string; muted: boolean }) {
  return (
    <span className="d-inline-flex align-items-center gap-1 small" style={{ opacity: muted ? 0.45 : 1 }}>
      <span className="legend-dot" style={{ backgroundColor: color }} />
      {label}
    </span>
  );
}
