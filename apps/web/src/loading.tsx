import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

export function LoadingNote({ label = "Yükleniyor…" }: { label?: string }) {
  return (
    <Stack direction="row" spacing={1.5} sx={{ alignItems: "center", px: 2, py: 2 }}>
      <CircularProgress size={18} />
      <Typography color="text.secondary">{label}</Typography>
    </Stack>
  );
}
