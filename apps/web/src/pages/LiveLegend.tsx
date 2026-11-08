import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
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
    <Stack spacing={1} sx={{ px: 2, pb: 1.5 }}>
      <Stack spacing={0.5}>
        <Typography variant="caption" color="text.secondary">
          Durum
        </Typography>
        <Stack direction="row" sx={{ flexWrap: "wrap", gap: 1 }}>
          {VEHICLE_STATE_ORDER.map((state) => (
            <ChipRow
              key={state}
              color={VEHICLE_STATE_COLOR[state]}
              label={`${VEHICLE_STATE_LABEL[state]} ${dutyCounts.get(state) ?? 0}`}
              muted={!dutyCounts.get(state)}
            />
          ))}
        </Stack>
      </Stack>
      <Stack spacing={0.5}>
        <Typography variant="caption" color="text.secondary">
          Hareket
        </Typography>
        <Stack direction="row" sx={{ flexWrap: "wrap", gap: 1 }}>
          {MOTION_STATE_ORDER.map((state) => (
            <ChipRow
              key={state}
              color={MOTION_STATE_COLOR[state]}
              label={`${MOTION_STATE_LABEL[state]} ${motionCounts.get(state) ?? 0}`}
              muted={!motionCounts.get(state)}
            />
          ))}
        </Stack>
      </Stack>
    </Stack>
  );
}

function ChipRow({ color, label, muted }: { color: string; label: string; muted: boolean }) {
  return (
    <Stack direction="row" spacing={0.5} sx={{ alignItems: "center", opacity: muted ? 0.45 : 1 }}>
      <Box sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: color }} />
      <Typography variant="caption">{label}</Typography>
    </Stack>
  );
}
