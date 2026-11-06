import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

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
    <Stack
      direction={stacked ? "column" : "row"}
      spacing={stacked ? 1.5 : 1.25}
      sx={{ alignItems: stacked ? "center" : "center" }}
    >
      <Box
        component="img"
        src="/logo.png"
        alt=""
        width={size}
        height={size}
        sx={{ display: "block", borderRadius: 1.5, flexShrink: 0 }}
      />
      {withWordmark ? (
        <Typography
          component="span"
          sx={{
            fontFamily: '"Barlow", sans-serif',
            fontWeight: 800,
            fontSize: stacked ? "1.75rem" : "1.25rem",
            letterSpacing: -0.4,
            lineHeight: 1,
            color: "text.primary",
          }}
        >
          Backhaul
        </Typography>
      ) : null}
    </Stack>
  );
}
