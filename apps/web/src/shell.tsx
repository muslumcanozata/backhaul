import { ReactNode, useState } from "react";
import {
  CCloseButton,
  CContainer,
  CFooter,
  CHeader,
  CHeaderNav,
  CHeaderToggler,
  CNavItem,
  CNavLink,
  CSidebar,
  CSidebarBrand,
  CSidebarHeader,
  CSidebarNav,
  CSidebarToggler,
} from "@coreui/react";
import CIcon from "@coreui/icons-react";
import {
  cilArrowBottom,
  cilArrowTop,
  cilBuilding,
  cilChart,
  cilClipboard,
  cilAccountLogout,
  cilMap,
  cilMenu,
  cilSettings,
  cilSpeedometer,
  cilTruck,
  cilUser,
  cilPeople,
} from "@coreui/icons";
import SimpleBar from "simplebar-react";
import "simplebar-react/dist/simplebar.min.css";
import { BrandLogo } from "./brand";
import { PAGE_LABEL, ROLE_LABEL } from "./labels";
import { AlertBell } from "./pages/AlertBell";
import type { Page, User } from "./types";

const ICONS: Record<Page, string[]> = {
  firmalar: cilBuilding,
  masa: cilSpeedometer,
  gidis: cilArrowTop,
  donus: cilArrowBottom,
  takip: cilMap,
  araclar: cilTruck,
  soforler: cilUser,
  takograf: cilClipboard,
  raporlar: cilChart,
  ayarlar: cilSettings,
  kullanicilar: cilPeople,
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
  const [sidebarShow, setSidebarShow] = useState(true);
  const [unfoldable, setUnfoldable] = useState(false);

  function open(next: Page) {
    onOpen(next);
    if (window.matchMedia("(max-width: 991.98px)").matches) setSidebarShow(false);
  }

  return (
    <>
      <CSidebar
        className="border-end"
        colorScheme="dark"
        position="fixed"
        unfoldable={unfoldable}
        visible={sidebarShow}
        onVisibleChange={setSidebarShow}
      >
        <CSidebarHeader className="border-bottom">
          <CSidebarBrand className="text-decoration-none">
            <BrandLogo size={28} />
          </CSidebarBrand>
          <CCloseButton className="d-lg-none" dark onClick={() => setSidebarShow(false)} />
        </CSidebarHeader>
        <SimpleBar className="flex-grow-1">
          <CSidebarNav>
            {pages.map((item) => (
              <CNavItem key={item}>
                <CNavLink
                  href={`#${item}`}
                  active={item === page}
                  onClick={(event) => {
                    event.preventDefault();
                    open(item);
                  }}
                  style={{ cursor: "pointer" }}
                >
                  <CIcon customClassName="nav-icon" icon={ICONS[item]} />
                  {PAGE_LABEL[item]}
                </CNavLink>
              </CNavItem>
            ))}
            <CNavItem className="mt-auto">
              <CNavLink
                href="#logout"
                onClick={(event) => {
                  event.preventDefault();
                  onLogout();
                }}
                style={{ cursor: "pointer" }}
              >
                <CIcon customClassName="nav-icon" icon={cilAccountLogout} />
                Çıkış
              </CNavLink>
            </CNavItem>
          </CSidebarNav>
        </SimpleBar>
        <CSidebarHeader className="border-top d-none d-lg-flex">
          <CSidebarToggler onClick={() => setUnfoldable((value) => !value)} />
        </CSidebarHeader>
      </CSidebar>

      <div className="wrapper d-flex flex-column min-vh-100">
        <CHeader position="sticky" className="mb-4 p-0 border-bottom">
          <CContainer className="px-4" fluid>
            <CHeaderToggler onClick={() => setSidebarShow((value) => !value)} style={{ marginInlineStart: "-14px" }}>
              <CIcon icon={cilMenu} size="lg" />
            </CHeaderToggler>
            <CHeaderNav className="ms-auto align-items-center gap-3">
              {user.role !== "platform_admin" ? <AlertBell /> : null}
              <div className="d-none d-sm-block text-end">
                <div className="fw-semibold small">{user.email}</div>
                <div className="text-body-secondary small">{ROLE_LABEL[user.role]}</div>
              </div>
              <div
                className="rounded-circle bg-primary text-white d-inline-flex align-items-center justify-content-center"
                style={{ width: 36, height: 36, fontSize: 14 }}
              >
                {user.email.slice(0, 1).toUpperCase()}
              </div>
            </CHeaderNav>
          </CContainer>
          <CContainer className="px-4" fluid>
            <strong>{PAGE_LABEL[page]}</strong>
          </CContainer>
        </CHeader>

        <div className="body flex-grow-1">
          <CContainer className="px-4" fluid>
            {children}
          </CContainer>
        </div>

        <CFooter className="px-4">
          <div>
            <span className="ms-1">Backhaul</span>
          </div>
          <div className="ms-auto">
            <span className="text-body-secondary small">{user.role === "platform_admin" ? "Sicil" : "Sefer masası"}</span>
          </div>
        </CFooter>
      </div>
    </>
  );
}

export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="auth-layout">
      <div className="p-3 p-sm-4">
        <BrandLogo size={36} />
      </div>
      <div className="flex-grow-1 d-flex align-items-center justify-content-center px-3 py-4 py-md-5">
        <div style={{ width: "100%", maxWidth: 420 }}>{children}</div>
      </div>
    </div>
  );
}
