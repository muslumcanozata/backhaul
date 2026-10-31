from dataclasses import dataclass

from sqlalchemy.orm import Session

import app.arvento as arvento
import app.seyir as seyir
from app.config import Settings
from app.models import TenantSettings


@dataclass
class ProviderResult:
    provider: str
    updated: int
    unmatched: list[str]
    error: str | None = None


def enabled_providers(settings_row: TenantSettings) -> list[str]:
    found: list[str] = []
    if settings_row.arvento_enabled:
        found.append("arvento")
    if settings_row.seyir_enabled:
        found.append("seyir")
    return found


def pull_all(db: Session, tenant_id, settings_row: TenantSettings, app_settings: Settings, opener=None) -> tuple[int, list[str], list[ProviderResult]]:
    results: list[ProviderResult] = []
    if settings_row.arvento_enabled:
        results.append(_pull_arvento(db, tenant_id, app_settings, opener))
    if settings_row.seyir_enabled:
        results.append(_pull_seyir(db, tenant_id, settings_row, app_settings, opener))
    if not results:
        raise RuntimeError("Açık konum sağlayıcısı yok")
    updated = sum(item.updated for item in results)
    unmatched = [f"{item.provider}:{plate}" for item in results for plate in item.unmatched if plate]
    return updated, unmatched, results


def _pull_arvento(db: Session, tenant_id, app_settings: Settings, opener) -> ProviderResult:
    try:
        username, pin1, pin2 = arvento.credentials(db, tenant_id, app_settings)
        if opener is None:
            packets = arvento.fetch_packets(username, pin1, pin2)
        else:
            packets = arvento.fetch_packets(username, pin1, pin2, opener=opener)
        updated, unmatched = arvento.apply_packets(db, tenant_id, packets)
        return ProviderResult("arvento", updated, unmatched)
    except arvento.MissingSecret as exc:
        return ProviderResult("arvento", 0, [], str(exc))
    except arvento.ArventoError as exc:
        return ProviderResult("arvento", 0, [], str(exc))


def _pull_seyir(db: Session, tenant_id, settings_row: TenantSettings, app_settings: Settings, opener) -> ProviderResult:
    try:
        username, password = seyir.credentials(db, tenant_id, app_settings)
        if opener is None:
            packets = seyir.fetch_packets(username, password)
            tacho = seyir.fetch_tacho(username, password)
        else:
            packets = seyir.fetch_packets(username, password, opener=opener)
            tacho = seyir.fetch_tacho(username, password, opener=opener)
        updated, unmatched = seyir.apply_packets(db, tenant_id, packets)
        seyir.apply_tacho(db, tenant_id, tacho, settings_row)
        return ProviderResult("seyir", updated, unmatched)
    except seyir.MissingSecret as exc:
        return ProviderResult("seyir", 0, [], str(exc))
    except seyir.SeyirError as exc:
        return ProviderResult("seyir", 0, [], str(exc))
