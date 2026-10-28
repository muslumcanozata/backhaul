import { createTheme } from "@mui/material/styles";

// Palette and type adapted from Minimal Free (MIT).
// https://github.com/minimal-ui-kit/material-kit-react

const primary = {
  lighter: "#D0ECFE",
  light: "#73BAFB",
  main: "#1877F2",
  dark: "#0C44AE",
  darker: "#042174",
};

const grey = {
  50: "#FCFDFD",
  100: "#F9FAFB",
  200: "#F4F6F8",
  300: "#DFE3E8",
  400: "#C4CDD5",
  500: "#919EAB",
  600: "#637381",
  700: "#454F5B",
  800: "#1C252E",
  900: "#141A21",
};

const cardShadow = "0 0 2px 0 rgba(145, 158, 171, 0.2), 0 12px 24px -4px rgba(145, 158, 171, 0.12)";

export const drawer = {
  width: 280,
  selected: "rgba(24, 119, 242, 0.08)",
  hover: "rgba(24, 119, 242, 0.16)",
};

export const theme = createTheme({
  breakpoints: { values: { xs: 0, sm: 600, md: 900, lg: 1200, xl: 1536 } },
  shape: { borderRadius: 8 },
  typography: {
    fontFamily: '"DM Sans Variable", "DM Sans", sans-serif',
    fontWeightLight: 300,
    fontWeightRegular: 400,
    fontWeightMedium: 500,
    fontWeightBold: 700,
    h3: { fontFamily: '"Barlow", sans-serif', fontWeight: 700, fontSize: "1.5rem", lineHeight: 1.5 },
    h4: { fontWeight: 700, fontSize: "1.25rem", lineHeight: 1.5 },
    h5: { fontWeight: 700, fontSize: "1.125rem", lineHeight: 1.5 },
    h6: { fontWeight: 600, fontSize: "1.0625rem", lineHeight: 1.56 },
    subtitle1: { fontSize: "1rem", fontWeight: 600, lineHeight: 1.5 },
    subtitle2: { fontSize: "0.875rem", fontWeight: 600, lineHeight: 1.57 },
    body1: { fontSize: "1rem", lineHeight: 1.5 },
    body2: { fontSize: "0.875rem", lineHeight: 1.57 },
    caption: { fontSize: "0.75rem", lineHeight: 1.5 },
    button: { fontWeight: 700, textTransform: "unset" },
  },
  palette: {
    mode: "light",
    primary: { light: primary.light, main: primary.main, dark: primary.dark, contrastText: "#FFFFFF" },
    secondary: { light: "#C684FF", main: "#8E33FF", dark: "#5119B7", contrastText: "#FFFFFF" },
    info: { light: "#61F3F3", main: "#00B8D9", dark: "#006C9C", contrastText: "#FFFFFF" },
    success: { light: "#77ED8B", main: "#22C55E", dark: "#118D57", contrastText: "#FFFFFF" },
    warning: { light: "#FFD666", main: "#FFAB00", dark: "#B76E00", contrastText: "#1C252E" },
    error: { light: "#FFAC82", main: "#FF5630", dark: "#B71D18", contrastText: "#FFFFFF" },
    grey,
    divider: "rgba(145, 158, 171, 0.2)",
    text: { primary: grey[800], secondary: grey[600], disabled: grey[500] },
    background: { default: grey[100], paper: "#FFFFFF" },
    action: {
      hover: "rgba(145, 158, 171, 0.08)",
      selected: "rgba(145, 158, 171, 0.16)",
      disabled: "rgba(145, 158, 171, 0.8)",
      disabledBackground: "rgba(145, 158, 171, 0.24)",
    },
  },
  components: {
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: ({ ownerState }) => ({
          fontWeight: 700,
          textTransform: "unset",
          borderRadius: 8,
          ...(ownerState.variant === "contained" && ownerState.color === "inherit"
            ? {
                color: "#FFFFFF",
                backgroundColor: grey[800],
                "&:hover": { backgroundColor: grey[700], color: "#FFFFFF" },
              }
            : {}),
        }),
        sizeLarge: { minHeight: 48 },
      },
    },
    MuiCard: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: {
          position: "relative",
          zIndex: 0,
          borderRadius: 16,
          boxShadow: cardShadow,
          backgroundImage: "none",
          border: "none",
        },
      },
    },
    MuiCardHeader: {
      styleOverrides: { root: { padding: "24px 24px 0" } },
    },
    MuiCardContent: {
      styleOverrides: { root: { padding: 24, "&:last-child": { paddingBottom: 24 } } },
    },
    MuiPaper: {
      defaultProps: { elevation: 0 },
      styleOverrides: { root: { backgroundImage: "none" } },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: { borderRadius: 8 },
        notchedOutline: { borderColor: "rgba(145, 158, 171, 0.2)" },
      },
    },
    MuiCssBaseline: {
      styleOverrides: {
        html: { height: "100%" },
        body: { height: "100%", backgroundColor: grey[100] },
        "#root": { height: "100%" },
      },
    },
  },
});
