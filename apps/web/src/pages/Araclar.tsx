import { FormEvent, useEffect, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CardHeader from "@mui/material/CardHeader";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { api } from "../api";
import { useFleet } from "../fleet-data";
import { STATUS_LABEL, TRAILER_LABEL, availability, canWriteMaster, driverName } from "../labels";
import { useSession } from "../session";
import { VehicleFile } from "./VehicleFile";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function isVehicleId(value: string) {
  return UUID_RE.test(value);
}

export function Araclar({ initialFilter = "" }: { initialFilter?: string }) {
  const { token, user, notice } = useSession();
  const { vehicles, drivers, settings, reload } = useFleet();
  const [selected, setSelected] = useState(() => (isVehicleId(initialFilter) ? initialFilter : ""));
  const [filter, setFilter] = useState(() => (isVehicleId(initialFilter) ? "" : initialFilter));
  const [plate, setPlate] = useState("");
  const [capacity, setCapacity] = useState("24");
  const [trailer, setTrailer] = useState(settings?.enabled_trailer_types[0] ?? "tenteli");
  const vehicle = vehicles.find((item) => item.id === selected);
  const types = settings?.enabled_trailer_types ?? ["tenteli"];

  useEffect(() => {
    if (isVehicleId(initialFilter)) {
      setSelected(initialFilter);
      setFilter("");
    } else {
      setFilter(initialFilter);
      if (initialFilter) setSelected("");
    }
  }, [initialFilter]);

  const groups = useMemo(() => {
    const map = new Map<string, number>();
    vehicles.forEach((item) => {
      const label = availability(item, settings);
      map.set(label, (map.get(label) ?? 0) + 1);
    });
    return map;
  }, [vehicles, settings]);

  const shown = filter ? vehicles.filter((item) => availability(item, settings) === filter) : vehicles;

  function chooseFilter(next: string) {
    setFilter(next);
    setSelected("");
    window.location.hash = next ? `araclar/${encodeURIComponent(next)}` : "araclar";
  }

  function openVehicle(id: string) {
    setSelected(id);
    window.location.hash = `araclar/${id}`;
  }

  function closeVehicle() {
    setSelected("");
    window.location.hash = filter ? `araclar/${encodeURIComponent(filter)}` : "araclar";
  }

  useEffect(() => {
    if (!types.includes(trailer)) setTrailer(types[0]);
  }, [types, trailer]);

  async function create(event: FormEvent) {
    event.preventDefault();
    notice("");
    try {
      const created = await api<{ id: string }>("/vehicles", token, {
        method: "POST",
        body: JSON.stringify({ plate, capacity_tons: capacity, trailer_type: trailer }),
      });
      setPlate("");
      await reload();
      openVehicle(created.id);
    } catch (err) {
      notice(err instanceof Error ? err.message : "Araç eklenemedi");
    }
  }

  if (selected && vehicle) {
    return (
      <Stack spacing={2}>
        <VehicleFile vehicle={vehicle} drivers={drivers} settings={settings} onChanged={reload} onClose={closeVehicle} />
      </Stack>
    );
  }

  if (selected && !vehicle) {
    return (
      <Card>
        <CardContent>
          <Stack spacing={2}>
            <Typography color="text.secondary">Araç bulunamadı.</Typography>
            <Button onClick={closeVehicle}>Listeye dön</Button>
          </Stack>
        </CardContent>
      </Card>
    );
  }

  return (
    <Box sx={{ display: "grid", gap: 3, gridTemplateColumns: { xs: "1fr", lg: canWriteMaster(user.role) ? "1.4fr 0.8fr" : "1fr" } }}>
      <Card>
        <CardHeader title="Araçlar" subheader="Özlük dosyası için bir araç seçin." />
        <Stack direction="row" sx={{ flexWrap: "wrap", gap: 1, px: 2, pb: 1 }}>
          <Chip label={`Tümü ${vehicles.length}`} color={filter ? "default" : "primary"} onClick={() => chooseFilter("")} />
          {[...groups.entries()].map(([label, count]) => (
            <Chip key={label} label={`${label} ${count}`} color={filter === label ? "primary" : "default"} onClick={() => chooseFilter(label)} />
          ))}
          {filter && !groups.has(filter) ? <Chip label={`${filter} 0`} color="primary" onClick={() => chooseFilter("")} /> : null}
        </Stack>
        <List>
          {shown.map((item) => (
            <ListItemButton key={item.id} onClick={() => openVehicle(item.id)}>
              <Stack>
                <Typography variant="subtitle2">{item.plate}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {TRAILER_LABEL[item.trailer_type] ?? item.trailer_type} · {item.capacity_tons} ton · {STATUS_LABEL[item.status] ?? item.status} ·{" "}
                  {driverName(drivers, item.driver_id)} · {availability(item, settings)}
                </Typography>
              </Stack>
            </ListItemButton>
          ))}
        </List>
        {shown.length === 0 ? (
          <CardContent>
            <Typography color="text.secondary">{vehicles.length === 0 ? "Kayıtlı araç yok." : "Bu durumda araç yok."}</Typography>
          </CardContent>
        ) : null}
      </Card>
      {canWriteMaster(user.role) ? (
        <Card component="form" onSubmit={create}>
          <CardHeader title="Araç ekle" />
          <CardContent>
            <Stack spacing={2}>
              <TextField label="Plaka" value={plate} onChange={(event) => setPlate(event.target.value)} required />
              <TextField label="Kapasite (ton)" value={capacity} onChange={(event) => setCapacity(event.target.value)} required />
              <TextField select label="Kasa" value={types.includes(trailer) ? trailer : types[0]} onChange={(event) => setTrailer(event.target.value)}>
                {types.map((type) => (
                  <MenuItem key={type} value={type}>
                    {TRAILER_LABEL[type] ?? type}
                  </MenuItem>
                ))}
              </TextField>
              <Button type="submit" variant="contained">
                Ekle
              </Button>
            </Stack>
          </CardContent>
        </Card>
      ) : null}
    </Box>
  );
}
