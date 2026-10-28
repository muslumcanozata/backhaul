import { ReactNode, useState } from "react";
import { ArrowCircleDownIcon, ArrowCircleUpIcon, BuildingsIcon, GearSixIcon, Icon, ListIcon, MapTrifoldIcon, SquaresFourIcon, SteeringWheelIcon, TruckIcon, UsersThreeIcon, WarningIcon } from "@phosphor-icons/react";
import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Drawer from "@mui/material/Drawer";
import IconButton from "@mui/material/IconButton";
import ListItemButton from "@mui/material/ListItemButton";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { PAGE_LABEL, ROLE_LABEL } from "./labels";
import { drawer } from "./theme";
import type { Page, User } from "./types";

const ICONS: Record<Page, Icon> = {
  firmalar: BuildingsIcon,
  masa: SquaresFourIcon,
  gidis: ArrowCircleUpIcon,
  donus: ArrowCircleDownIcon,
  takip: MapTrifoldIcon,
  uyarilar: WarningIcon,
  araclar: TruckIcon,
  soforler: SteeringWheelIcon,
  ayarlar: GearSixIcon,
  kullanicilar: UsersThreeIcon,
};

export function Dashboard({
  user,
  pages,
  page,
  onOpen,
  onLogout,
  children,
}: {
  user: User;
  pages: Page[];
  page: Page;
  onOpen: (page: Page) => void;
  onLogout: () => void;
  children: ReactNode;
}) {
  const [mobileOpen, setMobileOpen] = useState(false);

  function open(next: Page) {
    onOpen(next);
    setMobileOpen(false);
  }

  return (
    <Box sx={{ display: "flex", minHeight: "100%", bgcolor: "background.default" }}>
      <Box sx={{ display: { xs: "none", lg: "flex" }, width: drawer.width, flexShrink: 0 }}>
        <NavBody user={user} pages={pages} page={page} onOpen={open} onLogout={onLogout} />
      </Box>
      <Drawer open={mobileOpen} onClose={() => setMobileOpen(false)} sx={{ display: { lg: "none" } }} slotProps={{ paper: { sx: { width: drawer.width } } }}>
        <NavBody user={user} pages={pages} page={page} onOpen={open} onLogout={onLogout} />
      </Drawer>
      <Box sx={{ display: "flex", flex: "1 1 auto", flexDirection: "column", minWidth: 0 }}>
        <Box
          component="header"
          sx={{
            position: "sticky",
            top: 0,
            zIndex: 1100,
            height: 64,
            display: "flex",
            alignItems: "center",
            px: { xs: 2, sm: 3 },
            bgcolor: "rgba(255,255,255,0.8)",
            backdropFilter: "blur(6px)",
            borderBottom: "1px dashed",
            borderColor: "divider",
          }}
        >
          <Stack direction="row" sx={{ width: 1, alignItems: "center", justifyContent: "space-between" }}>
            <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
              <IconButton onClick={() => setMobileOpen(true)} sx={{ display: { lg: "none" }, ml: -1 }} aria-label="Menü">
                <ListIcon />
              </IconButton>
              <Typography variant="h6">{PAGE_LABEL[page]}</Typography>
            </Stack>
            <Stack direction="row" spacing={1.5} sx={{ alignItems: "center" }}>
              <Box sx={{ textAlign: "right", display: { xs: "none", sm: "block" } }}>
                <Typography variant="subtitle2">{user.email}</Typography>
                <Typography variant="caption" color="text.secondary">
                  {ROLE_LABEL[user.role]}
                </Typography>
              </Box>
              <Avatar sx={{ bgcolor: "primary.main", width: 36, height: 36, fontSize: 14 }}>{user.email.slice(0, 1).toUpperCase()}</Avatar>
            </Stack>
          </Stack>
        </Box>
        <Box component="main" sx={{ flex: "1 1 auto", px: { xs: 2, sm: 3, lg: 5 }, py: { xs: 2, sm: 3 }, pb: { xs: 6, sm: 8 } }}>
          {children}
        </Box>
      </Box>
    </Box>
  );
}

function NavBody({
  user,
  pages,
  page,
  onOpen,
  onLogout,
}: {
  user: User;
  pages: Page[];
  page: Page;
  onOpen: (page: Page) => void;
  onLogout: () => void;
}) {
  return (
    <Box
      sx={{
        bgcolor: "background.paper",
        borderRight: "1px solid",
        borderColor: "divider",
        display: "flex",
        flexDirection: "column",
        height: "100%",
        width: drawer.width,
        position: { lg: "fixed" },
        top: 0,
        left: 0,
        pt: 2.5,
        px: 2.5,
      }}
    >
      <Stack spacing={0.25} sx={{ px: 1, mb: 2 }}>
        <Typography variant="h6" sx={{ fontWeight: 800, letterSpacing: -0.2 }}>
          Backhaul
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {user.role === "platform_admin" ? "Sicil" : "Sefer masası"}
        </Typography>
      </Stack>
      <Stack component="nav" spacing={0.5} sx={{ flex: "1 1 auto" }}>
        {pages.map((item) => (
          <NavButton key={item} item={item} active={item === page} onClick={() => onOpen(item)} />
        ))}
      </Stack>
      <Box sx={{ pb: 2 }}>
        <NavButton item={null} label="Çıkış" active={false} onClick={onLogout} />
      </Box>
    </Box>
  );
}

function NavButton({ item, label, active, onClick }: { item: Page | null; label?: string; active: boolean; onClick: () => void }) {
  const ActiveIcon = item ? ICONS[item] : null;
  return (
    <ListItemButton
      selected={active}
      onClick={onClick}
      disableGutters
      sx={{
        flex: "0 0 auto",
        minHeight: 44,
        px: 2,
        py: 1,
        gap: 2,
        borderRadius: 0.75,
        color: active ? "primary.main" : "text.secondary",
        typography: "body2",
        fontWeight: active ? 600 : 500,
        "&.Mui-selected": { bgcolor: drawer.selected },
        "&.Mui-selected:hover": { bgcolor: drawer.hover },
        "&:hover": { bgcolor: drawer.selected },
      }}
    >
      {ActiveIcon ? (
        <Box sx={{ width: 24, height: 24, display: "inline-flex", alignItems: "center", justifyContent: "center", color: "inherit" }}>
          <ActiveIcon size={20} weight={active ? "fill" : "regular"} />
        </Box>
      ) : null}
      <Box component="span" sx={{ flexGrow: 1 }}>
        {label ?? (item ? PAGE_LABEL[item] : "")}
      </Box>
    </ListItemButton>
  );
}

export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <Box sx={{ minHeight: "100%", bgcolor: "background.default" }}>
      <Stack sx={{ minHeight: "100%" }}>
        <Box sx={{ px: 3, pt: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 800, letterSpacing: -0.2 }}>
            Backhaul
          </Typography>
        </Box>
        <Box sx={{ display: "flex", flex: "1 1 auto", alignItems: "center", justifyContent: "center", p: { xs: 2, sm: 3 }, pb: 10 }}>
          <Box sx={{ width: "100%", maxWidth: 420 }}>{children}</Box>
        </Box>
      </Stack>
    </Box>
  );
}
