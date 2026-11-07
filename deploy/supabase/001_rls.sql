-- Backhaul + Supabase RLS ve Realtime yetkisi.
-- SQLAlchemy create_all şemayı oluşturduktan sonra Dashboard → SQL Editor'da çalıştır.
-- Web tablolara doğrudan gitmez; anon SELECT kapalıdır. Auth kullanıcıları kendi firmasını okuyabilir.

alter table if exists public.users enable row level security;
alter table if exists public.tenants enable row level security;
alter table if exists public.tenant_settings enable row level security;
alter table if exists public.vehicles enable row level security;
alter table if exists public.drivers enable row level security;
alter table if exists public.vehicle_positions enable row level security;
alter table if exists public.loads enable row level security;
alter table if exists public.tacho_states enable row level security;
alter table if exists public.tacho_samples enable row level security;
alter table if exists public.alerts enable row level security;
alter table if exists public.tenant_secrets enable row level security;
alter table if exists public.sms_outbox enable row level security;
alter table if exists public.road_cache enable row level security;
alter table if exists public.routes_usage enable row level security;
alter table if exists public.vehicle_maintenances enable row level security;
alter table if exists public.vehicle_tire_events enable row level security;
alter table if exists public.vehicle_fuel_fills enable row level security;
alter table if exists public.vehicle_fuel_samples enable row level security;
alter table if exists public.vehicle_driver_stints enable row level security;

-- Kendi kullanıcı satırı
drop policy if exists users_self on public.users;
create policy users_self on public.users
  for select to authenticated
  using (id = auth.uid());

-- Operasyon tabloları: tenant_id eşleşmesi
drop policy if exists vehicles_tenant on public.vehicles;
create policy vehicles_tenant on public.vehicles
  for select to authenticated
  using (tenant_id = (select u.tenant_id from public.users u where u.id = auth.uid()));

drop policy if exists drivers_tenant on public.drivers;
create policy drivers_tenant on public.drivers
  for select to authenticated
  using (tenant_id = (select u.tenant_id from public.users u where u.id = auth.uid()));

drop policy if exists positions_tenant on public.vehicle_positions;
create policy positions_tenant on public.vehicle_positions
  for select to authenticated
  using (
    vehicle_id in (
      select v.id from public.vehicles v
      where v.tenant_id = (select u.tenant_id from public.users u where u.id = auth.uid())
    )
  );

drop policy if exists loads_tenant on public.loads;
create policy loads_tenant on public.loads
  for select to authenticated
  using (tenant_id = (select u.tenant_id from public.users u where u.id = auth.uid()));

-- Not: realtime.messages sahibi SQL Editor rolü değil; ALTER/POLICY orada 42501 verir.
-- Canlı harita public broadcast kullanır (kanal adı tenant:<uuid>, yalnız /live/config ile gelir).
